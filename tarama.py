import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": [{"url": data.get("logo")}] if data.get("logo") else [],
            "platform": data.get("platform")
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def veri_ayikla(html, link, platform_adi):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Başlık ve Gereksiz Sayfa Filtresi
    unvan = soup.select_one('h1.elementor-heading-title') or soup.select_one('h1')
    unvan_text = unvan.get_text(strip=True) if unvan else ""
    
    yasakli = ['bülten', 'haber', 'duyuru', 'komite', 'üyelik', 'etik', 'vizyon', 'iletisim', 'yaka-is']
    if not unvan_text or any(x in unvan_text.lower() for x in yasakli):
        return None

    logo_url, web_url = "", ""

    # 2. LOGO AVCISI (Senin gönderdiğin srcset yapısına göre)
    img_tag = soup.select_one('.elementor-widget-image img')
    if img_tag:
        srcset = img_tag.get('srcset')
        if srcset:
            # Virgülle ayrılan linkleri listeye al ve en sondakini (en büyük olanı) seç
            parts = [p.strip().split(' ')[0] for p in srcset.split(',')]
            logo_url = parts[-1] 
        else:
            logo_url = img_tag.get('src') or img_tag.get('data-src')

        # Linki temizle: -300x300 gibi boyutları SİL, sadece saf dosya ismini bırak
        if logo_url:
            logo_url = re.sub(r'-\d+x\d+', '', logo_url)
            logo_url = urljoin(link, logo_url)

    # 3. WEB URL (Tablo tarama)
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a = row.find('a')
            if a: web_url = a.get('href')
            break

    if not web_url: return None
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url, "platform": platform_adi}

def baslat():
    log("🚀 SON KURŞUN: PLATFORM & LOGO OPERASYONU")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'})

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "imder"},
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "isder"}
    ]

    for site in siteler:
        log(f"🔎 {site['platform'].upper()} taranıyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Daha esnek link toplama
            domain = site['platform'] + ".org.tr"
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if domain in h and len(h.strip('/').split('/')) >= 4:
                    if not any(x in h.lower() for x in ['page', 'etik', 'komite', 'bulten', 'haber']):
                        links.add(urljoin(site["url"], h))

            log(f"📦 {len(links)} adet potansiyel firma linki işleniyor...")

            for link in links:
                try:
                    detay_r = session.get(link, timeout=15, verify=False)
                    veri = veri_ayikla(detay_r.text, link, site['platform'])
                    if veri:
                        status = airtable_ekle(veri)
                        log(f"✅ [{veri['platform']}] {veri['firma_adi']} | Logo: {'Tamam' if veri['logo'] else 'Yok'} | Airtable: {status}")
                        time.sleep(1)
                except: continue
        except Exception as e: log(f"💥 Kritik Hata: {e}")

if __name__ == "__main__":
    baslat()
