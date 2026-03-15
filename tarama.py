import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
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
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    fields = {
        "firma_adi": data.get("firma_adi"),
        "web_url": data.get("web_url"),
        "platform": data.get("platform")
    }
    if data.get("logo"):
        fields["logo"] = [{"url": data.get("logo")}]
    try:
        res = requests.post(url, json={"fields": fields}, headers=headers, timeout=10)
        return "✅" if res.status_code in [200, 201] else f"❌ {res.status_code}"
    except: return "⚠️"

def veri_ayikla(html, sayfa_url, platform_adi):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('title')
    if not title: return None
    unvan = title.get_text().split('–')[0].split('|')[0].strip()
    
    # Çöp Filtresi
    if any(x in unvan.lower() for x in ["etik", "üyelik", "form", "kayıt", "hakkımızda", "tüzük", "isder", "imder"]):
        return None

    # Logo ve Web URL bulma (Güçlendirilmiş)
    logo_url = ""
    img = soup.select_one('.elementor-widget-image img')
    if img:
        logo_url = img.get('srcset', '').split(',')[-1].strip().split(' ')[0] or img.get('src', '')
        if logo_url:
            logo_url = urljoin(sayfa_url, logo_url)
            logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('.webp')[0]

    web_url = ""
    for a in soup.find_all('a', href=True):
        href = a['href']
        if "http" in href and not any(x in href.lower() for x in ['isder.org', 'imder.org', 'facebook', 'instagram', 'linkedin', 'twitter', 'google', 'youtube', 'makinebirlik']):
            web_url = href
            break
            
    if not web_url: return None
    return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url, "platform": platform_adi}

def baslat():
    log("🚀 OPERASYON BAŞLATILDI")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    hedefler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in hedefler:
        log(f"🔎 {hedef['platform']} Taranıyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Link yakalama filtresi: /isder/ veya /imder/ geçen tüm detay sayfaları
            links = {urljoin(hedef["url"], a['href']) for a in soup.find_all('a', href=True) 
                     if len(a['href'].split('/')) > 4 and not any(x in a['href'].lower() for x in ['haber', 'duyuru', 'etik', 'iletisim'])}

            for link in links:
                try:
                    res = session.get(link, timeout=15, verify=False)
                    veri = veri_ayikla(res.text, link, hedef['platform'])
                    if veri:
                        durum = airtable_ekle(veri)
                        log(f"{durum} {veri['firma_adi']}")
                        time.sleep(0.5)
                except: continue
        except Exception as e: log(f"Hata: {e}")

if __name__ == "__main__":
    baslat()
