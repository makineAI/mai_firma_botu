import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Sadece 3 temel sütun: İsim, Web ve Platform
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi", "Bilinmeyen"),
            "web_url": data.get("web_url", ""),
            "platform": data.get("platform", "")
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return "✅"
        else:
            return f"❌ ({res.status_code})"
    except:
        return "⚠️ Bağlantı Hatası"

def veri_ayikla(html, platform_adi):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Firma Adı
    title = soup.find('title')
    firma_adi = title.get_text().split('–')[0].strip() if title else "İsimsiz"

    # Gelişmiş Web Sitesi Bulucu
    web_url = ""
    # Tablodaki tüm linkleri tara
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Eğer link bir web sitesi gibi duruyorsa ve dernek linki değilse
        if "http" in href and not any(x in href for x in ['isder.org', 'imder.org', 'facebook', 'instagram', 'linkedin', 'twitter']):
            web_url = href
            break
            
    return {
        "firma_adi": firma_adi,
        "web_url": web_url,
        "platform": platform_adi
    }

def baslat():
    log("🚀 LOGOSUZ, SADE AKTARIM BAŞLADI")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    hedefler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in hedefler:
        log(f"🔎 {hedef['platform']} taranıyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if f"/{hedef['platform'].lower()}" in href.lower() and len(href.split('/')) > 4:
                    if not any(x in href.lower() for x in ['haber', 'etkinlik', 'iletisim']):
                        links.add(urljoin(hedef["url"], href))

            for link in links:
                try:
                    res_detay = session.get(link, timeout=20, verify=False)
                    veri = veri_ayikla(res_detay.text, hedef['platform'])
                    if veri:
                        durum = airtable_ekle(veri)
                        log(f"{durum} {veri['firma_adi']} -> {veri['web_url']}")
                        time.sleep(0.3)
                except: continue
        except Exception as e:
            log(f"Hata: {e}")

if __name__ == "__main__":
    baslat()
