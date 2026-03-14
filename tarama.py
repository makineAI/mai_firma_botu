import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Airtable Bilgileri ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    # Airtable logoyu 'Attachment' olarak bekler
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

def veri_ayikla(soup, site_id):
    # 1. Firma Unvanı
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']): return None

    # 2. Logo (Senin verdiğin nokta atışı yapılar)
    logo_url = ""
    # Her iki site için de ortak olan resim kutusunu bul
    img_container = soup.select_one('.elementor-widget-image img')
    
    if img_container:
        # ÖNCELİK: srcset (Senin gönderdiğin kodda temiz resimler burada)
        srcset = img_container.get('srcset')
        if srcset:
            # Virgülle ayrılan linklerden en temizini çek
            logo_url = srcset.split(',')[0].split(' ')[0].strip()
        
        # Eğer srcset yoksa src veya data-src bak
        if not logo_url or "data:image" in logo_url:
            logo_url = img_container.get('src') or img_container.get('data-src')

    # 3. Web Sitesi (Tablo içindeki Web Sitesi satırı)
    web_url = ""
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a_tag = row.find('a')
            web_url = a_tag['href'] if a_tag else row.find_all('td')[-1].get_text(strip=True)
            break
            
    if not web_url or "http" not in web_url: return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 LOGO GARANTİLİ TARAMA BAŞLADI")
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}

    siteler = [
        {"id": "imder", "url": "https://imder.org.tr/uyelerimiz/", "filtre": "imder.org.tr"},
        {"id": "isder", "url": "https://isder.org.tr/uyelerimiz/", "filtre": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['id'].upper()} taranıyor...")
        try:
            r = session.get(site["url"], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if site["filtre"] in h and len(h.split('/')) > 4:
                    if not any(x in h.lower() for x in ['page', 'etik', 'komite', 'uyelik']):
                        links.add(h)

            for link in links:
                try:
                    detay_r = session.get(link, headers=headers, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    veri = veri_ayikla(detay_soup, site['id'])
                    
                    if veri:
                        if veri["logo"] and not veri["logo"].startswith('http'):
                            veri["logo"] = urljoin(link, veri["logo"])
                        
                        status = airtable_ekle(veri)
                        log(f"   🏢 {veri['firma_adi']} | Logo: {'✅ OK' if veri['logo'] else '❌ YOK'}")
                        time.sleep(1)
                except: continue
        except Exception as e:
            log(f"❌ Hata: {e}")

if __name__ == "__main__":
    baslat()
