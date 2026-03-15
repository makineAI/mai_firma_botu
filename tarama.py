import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3
from urllib.parse import urljoin

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(unvan, web, platform):
    """Airtable'a sadece 3 bilgiyi gönderir."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": {
            "firma_adi": unvan,
            "web_url": web,
            "platform": platform
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        return "✅" if res.status_code in [200, 201] else f"❌ ({res.status_code})"
    except:
        return "⚠️"

def veri_ayikla(html, platform_adi):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Firma Ünvanını Al (Sayfa başlığından)
    title_tag = soup.find('title')
    if not title_tag: return None
    unvan = title_tag.get_text().split('–')[0].strip()

    # Çöp verileri engelle (Üyelik, Kayıt gibi sayfaları atla)
    if any(x in unvan.lower() for x in ["üyelik", "formu", "kayıt", "isimsiz", "hakkımızda"]):
        return None

    # 2. Web URL Bul (Sayfadaki ilk harici link)
    web_url = ""
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Dernek siteleri ve sosyal medya dışındaki ilk linki web sitesi kabul et
        if href.startswith("http") and not any(x in href for x in ['isder.org', 'imder.org', 'facebook', 'instagram', 'linkedin', 'twitter', 'google']):
            web_url = href
            break
            
    # Web sitesi yoksa o kaydı hiç alma (Doğru veri için)
    if not web_url:
        return None
            
    return {"unvan": unvan, "web": web_url}

def baslat():
    log("🚀 TARAMA BAŞLADI (SADECE ÜNVAN VE WEB URL)")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    siteler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in siteler:
        log(f"🔎 {hedef['platform']} inceleniyor...")
        try:
            r = session.get(hedef["url"], timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Detay sayfalarını topla
            linkler = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if f"/{hedef['platform'].lower()}" in h.lower() and len(h.split('/')) > 4:
                    if not any(x in h.lower() for x in ['haber', 'duyuru', 'iletisim']):
                        linkler.add(urljoin(hedef["url"], h))

            for l in linkler:
                try:
                    detay_r = session.get(l, timeout=15, verify=False)
                    sonuc = veri_ayikla(detay_r.text, hedef['platform'])
                    
                    if sonuc:
                        durum = airtable_ekle(sonuc['unvan'], sonuc['web'], hedef['platform'])
                        log(f"{durum} {sonuc['unvan']} -> {sonuc['web']}")
                        time.sleep(0.5)
                except: continue
        except Exception as e:
            log(f"Hata: {e}")

if __name__ == "__main__":
    baslat()
