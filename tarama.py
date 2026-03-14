import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
import re
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
    
    # Airtable 'Attachment' (Ek) alanı formatı
    # SÜTUN İSMİNİ BURADAN KONTROL ET: Eğer Airtable'da 'Logo' ise burayı da 'Logo' yap.
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
        if res.status_code not in [200, 201]:
            log(f"❌ Airtable Hatası ({res.status_code}): {res.text}")
        return res.status_code
    except Exception as e:
        log(f"❌ Airtable Bağlantı Hatası: {e}")
        return 500

def veri_ayikla(soup):
    # Başlık (Firma Adı)
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']):
        return None

    logo_url = ""
    web_url = ""
    
    inner_box = soup.select_one('.e-con-inner')
    if inner_box:
        # LOGO BULUCU
        img = inner_box.select_one('.elementor-widget-image img')
        if img:
            srcset = img.get('srcset')
            if srcset:
                logo_url = [p.strip().split(' ')[0] for p in srcset.split(',')][-1]
            else:
                logo_url = img.get('src') or img.get('data-src')
            
            # URL Temizliği (Airtable'ın sevmediği -300x300 gibi ekleri siler)
            if logo_url:
                logo_url = re.sub(r'-\d+x\d+', '', logo_url)

        # WEB URL BULUCU
        for row in inner_box.find_all('tr'):
            if "Web Sitesi" in row.get_text():
                a_tag = row.find('a')
                web_url = a_tag.get('href') if a_tag else row.find_all('td')[-1].get_text(strip=True)
                break

    if not web_url or "http" not in web_url:
        return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 İŞLEM BAŞLADI")
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "domain": "imder.org.tr"},
        {"url": "https://isder.org.tr/uyelerimiz/", "domain": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['domain']} taranıyor...")
        try:
            r = session.get(site["url"], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if site["domain"] in h and len(h.split('/')) > 4:
                    if not any(x in h.lower() for x in ['page', 'etik', 'komite', 'uyelik']):
                        links.add(h)

            log(f"📦 {len(links)} adet link bulundu. Detaylara giriliyor...")

            for link in links:
                try:
                    detay_r = session.get(link, headers=headers, timeout=15, verify=False)
                    veri = veri_ayikla(BeautifulSoup(detay_r.text, 'html.parser'))
                    
                    if veri:
                        if veri["logo"] and not veri["logo"].startswith('http'):
                            veri["logo"] = urljoin(link, veri["logo"])
                        
                        status = airtable_ekle(veri)
                        log(f"🏢 {veri['firma_adi']} -> Durum: {status}")
                        time.sleep(0.5)
                except Exception as e:
                    continue
        except Exception as e:
            log(f"❌ Ana sayfa hatası: {e}")

if __name__ == "__main__":
    baslat()
