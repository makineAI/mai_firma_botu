import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

processed_names = set()

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    # Airtable için logo formatı
    logo_field = [{"url": data.get("logo")}] if data.get("logo") else []

    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": logo_field
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def detay_sayfasi_coz(url, session, headers):
    try:
        r = session.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. FIRMA ADI
        unvan_tag = soup.select_one('h1.elementor-heading-title')
        unvan = unvan_tag.get_text(strip=True) if unvan_tag else None
        if not unvan or any(k in unvan.lower() for k in ['etik', 'komite', 'üyelik']): return None

        # 2. LOGO (SENİN ATTIĞIN NOKTA ATIŞI YAPI)
        logo_url = ""
        # Her iki dernek için de ortak olan ana widget kapsayıcısını bul
        logo_container = soup.select_one('.elementor-widget-image')
        if logo_container:
            img_tag = logo_container.find('img')
            if img_tag:
                # Srcset içindeki en temiz linki çek (Senin attığın .webp uzantılı linkler buradadır)
                srcset = img_tag.get('srcset')
                if srcset:
                    # Virgülle ayrılmış linklerden ilkini al
                    logo_url = srcset.split(',')[0].split(' ')[0].strip()
                else:
                    logo_url = img_tag.get('src')

        # 3. WEB URL (TABLO YAPISI)
        web_url = ""
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2 and "Web Sitesi" in cells[0].get_text():
                a_tag = cells[1].find('a')
                web_url = a_tag['href'] if a_tag else cells[1].get_text(strip=True)
                break
        
        if not web_url or "http" not in web_url: return None

        log(f"🏢 {unvan} | Logo: {'✅' if logo_url else '❌'} | Web: {web_url[:20]}")
        return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url}
    except: return None

def baslat():
    log("🚀 İMDER/İSDER Nokta Atışı Botu Başladı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    session = requests.Session()
    
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Tarama: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Sadece firma profil sayfalarını yakala
            links = []
            for a in soup.find_all('a', href=True):
                h = a['href']
                # Linkin derinliğini ve dernek URL'sini kontrol et
                if (h.startswith('https://isder.org.tr/') or h.startswith('https://imder.org.tr/')) and len(h.split('/')) > 4:
                    if not any(x in h.lower() for x in ['etik', 'komite', 'uyelik', 'page']):
                        links.append(h)

            for link in list(set(links)):
                veri = detay_sayfasi_coz(link, session, headers)
                if veri:
                    if airtable_ekle(veri) in [200, 201]:
                        log(f"   ✅ {veri['firma_adi']} Airtable'a eklendi.")
                        processed_names.add(veri['firma_adi'])
                    time.sleep(1)
        except Exception as e:
            log(f"❌ Hata: {e}")

if __name__ == "__main__":
    baslat()
