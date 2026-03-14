import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR (Airtable) ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

# --- SİTE TANIMLAMALARI (Yarın buraya 3, 4, 5 diye ekleme yapabilirsin) ---
SITELER = {
    "imder": {
        "ana_url": "https://imder.org.tr/uyelerimiz/",
        "logo_secici": ".elementor-widget-image img", 
        "unvan_secici": "h1.elementor-heading-title",
        "link_filtresi": "imder.org.tr"
    },
    "isder": {
        "ana_url": "https://isder.org.tr/uyelerimiz/",
        "logo_secici": ".elementor-widget-image img",
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
    """Sitenin kurallarına göre sayfadan bilgileri çeker."""
    
    # 1. Unvan
    unvan = soup.select_one(site_kurallari["unvan_secici"])
    unvan_text = unvan.get_text(strip=True) if unvan else None
    
    # Gereksiz sayfaları ele (Kurumsal sayfalar vb.)
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite', 'vizyon']):
        return None

    # 2. Logo (Srcset ve Lazy Load destekli)
    logo_url = ""
    img = soup.select_one(site_kurallari["logo_secici"])
    if img:
        srcset = img.get('srcset')
        if srcset:
            logo_url = srcset.split(',')[0].split(' ')[0].strip()
        else:
            logo_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')

    # 3. Web URL (Genel Tablo Mantığı - Çoğu sitede aynıdır)
    web_url = ""
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a = row.find('a')
            web_url = a['href'] if a else row.find_all('td')[-1].get_text(strip=True)
            break
            
    if not web_url or "http" not in web_url: return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 Çoklu Site Tarama Botu Başladı")
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}

    for site_id, kurallar in SITELER.items():
        log(f"🔎 {site_id.upper()} taranıyor...")
        try:
            r = session.get(kurallar["ana_url"], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Linkleri topla
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if kurallar["link_filtresi"] in href and len(href.split('/')) > 4:
                    if not any(x in href for x in ['page', 'etik', 'komite', 'uyelik']):
                        links.add(href)

            log(f"📦 {len(links)} adet potansiyel firma linki bulundu.")

            for link in links:
                try:
                    detay_r = session.get(link, headers=headers, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    veri = veri_ayikla(detay_soup, kurallar)
                    
                    if veri:
                        # Eksik URL tamamlama
                        if veri["logo"] and not veri["logo"].startswith('http'):
                            veri["logo"] = urljoin(link, veri["logo"])
                            
                        status = airtable_ekle(veri)
                        if status in [200, 201]:
                            log(f"   ✅ {veri['firma_adi']} kaydedildi.")
                        else:
                            log(f"   ❌ Airtable Hatası ({status}): {veri['firma_adi']}")
                        time.sleep(1)
                except:
                    continue
        except Exception as e:
            log(f"❌ {site_id} ana sayfa hatası: {e}")

if __name__ == "__main__":
    baslat()
