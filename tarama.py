import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Airtable Ayarları ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

# --- SİTE ÖZEL AYARLARI ---
# Yarın yeni site eklediğinde sadece buraya yeni bir blok eklemen yeterli.
SITELER = {
    "imder": {
        "ana_url": "https://imder.org.tr/uyelerimiz/",
        "logo_kabugu": 'div[data-id="523c0d9"]', # Senin verdiğin nokta atışı container ID
        "unvan_secici": "h1.elementor-heading-title",
        "link_filtresi": "imder.org.tr"
    },
    "isder": {
        "ana_url": "https://isder.org.tr/uyelerimiz/",
        "logo_kabugu": 'div[data-id="1f2d00b6"]', # Senin verdiğin nokta atışı container ID
        "unvan_secici": "h1.elementor-heading-title",
        "link_filtresi": "isder.org.tr"
    }
}

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
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

def veri_ayikla(soup, site_kurallari):
    # 1. Firma Unvanı
    unvan = soup.select_one(site_kurallari["unvan_secici"])
    unvan_text = unvan.get_text(strip=True) if unvan else None
    
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']):
        return None

    # 2. Logo (Nokta Atışı ID Kontrolü)
    logo_url = ""
    # Önce senin verdiğin data-id'li container'ı buluyoruz
    container = soup.select_one(site_kurallari["logo_kabugu"])
    if container:
        img = container.find("img")
        if img:
            # Srcset'teki en temiz .webp linkini alalım
            srcset = img.get('srcset')
            if srcset:
                logo_url = srcset.split(',')[0].split(' ')[0].strip()
            else:
                logo_url = img.get('src') or img.get('data-src')

    # 3. Web Sitesi (Tablo içinden)
    web_url = ""
    for row in soup.find_all('tr'):
        text = row.get_text()
        if "Web Sitesi" in text:
            a = row.find('a')
            web_url = a['href'] if a else row.find_all('td')[-1].get_text(strip=True)
            break
            
    if not web_url or "http" not in web_url: return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 Nokta Atışı Logo Avcısı Başladı")
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}

    for site_id, kurallar in SITELER.items():
        log(f"🔎 {site_id.upper()} taranıyor (Hedef ID: {kurallar['logo_kabugu']})")
        try:
            r = session.get(kurallar["ana_url"], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if kurallar["link_filtresi"] in h and len(h.split('/')) > 4:
                    if not any(x in h for x in ['page', 'etik', 'komite']):
                        links.add(h)

            for link in links:
                try:
                    detay_r = session.get(link, headers=headers, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    veri = veri_ayikla(detay_soup, kurallar)
                    
                    if veri:
                        if veri["logo"] and not veri["logo"].startswith('http'):
                            veri["logo"] = urljoin(link, veri["logo"])
                        
                        status = airtable_ekle(veri)
                        if status in [200, 201]:
                            log(f"   ✅ {veri['firma_adi']} (Logo: {'OK' if veri['logo'] else 'YOK'})")
                        time.sleep(0.5)
                except: continue
        except Exception as e:
            log(f"❌ {site_id} Hatası: {e}")

if __name__ == "__main__":
    baslat()
