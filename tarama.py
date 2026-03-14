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

def baslat():
    log("🚀 BULDOZER OPERASYONU BAŞLADI")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "imder"},
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "isder"}
    ]

    for site in siteler:
        log(f"🔎 {site['platform'].upper()} taranıyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Kartları bulmak için daha geniş bir ağ atıyoruz
            # Tüm 'article' etiketlerini veya içinde resim olan linkleri bul
            kartlar = soup.find_all('article')
            if not kartlar:
                # Alternatif: Eğer article yoksa, belirli bir class içeren div'lere bak
                kartlar = soup.find_all('div', class_=re.compile(r'elementor-post'))

            log(f"📦 {len(kartlar)} potansiyel firma bulundu.")

            for kart in kartlar:
                try:
                    # 1. LOGO YAKALAMA
                    img = kart.find('img')
                    logo_url = ""
                    if img:
                        # En iyi linki (srcset veya src) al
                        src_candidate = img.get('srcset', '').split(' ')[0] or img.get('src') or img.get('data-src')
                        if src_candidate:
                            logo_url = urljoin(site["url"], src_candidate)
                            # WordPress temizliği
                            logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('?')[0]

                    # 2. DETAY LİNKİ
                    link_tag = kart.find('a', href=True)
                    if not link_tag: continue
                    detay_link = urljoin(site["url"], link_tag['href'])

                    # Gereksiz linkleri ele
                    if any(x in detay_link for x in ['/page/', '/etik-', '/komite']): continue

                    # 3. İÇ SAYFADAN VERİ ÇEKME
                    detay_r = session.get(detay_link, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    
                    unvan = detay_soup.find('h1')
                    firma_adi = unvan.get_text(strip=True) if unvan else ""
                    
                    web_url = ""
                    for row in detay_soup.find_all('tr'):
                        if "Web Sitesi" in row.get_text():
                            a_tag = row.find('a')
                            web_url = a_tag.get('href') if a_tag else ""
                            break
                    
                    if firma_adi and web_url:
                        status = airtable_ekle({
                            "firma_adi": firma_adi,
                            "web_url": web_url,
                            "logo": logo_url,
                            "platform": site['platform']
                        })
                        log(f"✅ [{site['platform']}] {firma_adi} | Logo: {'EVET' if logo_url else 'HAYIR'} | Airtable: {status}")
                        time.sleep(1)

                except Exception as e: continue
        except Exception as e:
            log(f"💥 Liste Hatası: {e}")

if __name__ == "__main__":
    baslat()
