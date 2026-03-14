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
    
    # Airtable'da 'platform' isminde bir sütun açtığından emin ol
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
    
    # Başlık Çekme
    unvan = soup.select_one('h1.elementor-heading-title') or soup.select_one('h1')
    unvan_text = unvan.get_text(strip=True) if unvan else ""
    
    # Gereksiz sayfaları filtrele
    yasakli = ['bülten', 'haber', 'duyuru', 'komite', 'üyelik', 'etik', 'vizyon', 'iletisim', 'yaka-is']
    if not unvan_text or any(x in unvan_text.lower() for x in yasakli):
        return None

    logo_url, web_url = "", ""

    # --- NOKTA ATIŞI LOGO AVCISI ---
    # Senin verdiğin HTML yapısına göre 'img' etiketlerini tara
    images = soup.find_all('img')
    for img in images:
        srcset = img.get('srcset')
        src = img.get('src')
        
        # Eğer srcset varsa, en büyük resmi (genellikle en sonda 800w vb. olandır) bul
        if srcset:
            parts = srcset.split(',')
            # En son parçayı al (genellikle en kaliteli/temiz olan)
            last_part = parts[-1].strip().split(' ')[0]
            logo_url = last_part
        elif src:
            logo_url = src

        # Firma logosu olduğundan emin ol (site logosunu çekmemek için filtre)
        if logo_url and any(x in logo_url.lower() for x in ['uploads', 'member', 'uye', 'logo']):
            # Airtable için temizleme: -300x300 gibi boyut eklerini ve gereksiz uzantıları sil
            logo_url = re.sub(r'-\d+x\d+', '', logo_url)
            logo_url = urljoin(link, logo_url)
            break

    # --- WEB SİTESİ BULUCU ---
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a = row.find('a')
            if a: web_url = a.get('href')
            break

    if not web_url: return None
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url, "platform": platform_adi}

def baslat():
    log("🚀 PLATFORM VE LOGO ODAKLI OPERASYON BAŞLADI")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'})

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "imder"},
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "isder"}
    ]

    for site in siteler:
        log(f"🔎 {site['platform'].upper()} sitesi taranıyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Link toplama ve temizleme
            domain = site['platform'] + ".org.tr"
            links = {urljoin(site["url"], a['href']) for a in soup.find_all('a', href=True) 
                     if domain in a['href'] and len(a['href'].strip('/').split('/')) >= 3}

            for link in links:
                if any(x in link for x in ['/page/', '/etik-', '/komite', '/uyelik', '/iletisim']): continue
                try:
                    detay_r = session.get(link, timeout=15, verify=False)
                    veri = veri_ayikla(detay_r.text, link, site['platform'])
                    if veri:
                        status = airtable_ekle(veri)
                        log(f"✅ [{site['platform']}] {veri['firma_adi']} | Airtable: {status}")
                        time.sleep(1) # Airtable sınırı için
                except: continue
        except Exception as e: log(f"💥 Hata: {e}")

if __name__ == "__main__":
    baslat()
