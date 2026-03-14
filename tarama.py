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
    
    # Airtable Attachment formatı
    logo_field = [{"url": data.get("logo")}] if data.get("logo") and "http" in data.get("logo") else []

    payload = {
        "fields": {
            "firma_adi": str(data.get("firma_adi", ""))[:200],
            "web_url": str(data.get("web_url", "")),
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
        
        # 1. Firma Ünvanı
        unvan_tag = soup.find('h1', class_='elementor-heading-title')
        unvan = unvan_tag.text.strip() if unvan_tag else None
        if not unvan or unvan in processed_names: return None

        # 2. Logo Avcısı (Daha detaylı arama)
        logo_url = ""
        # Elementor resim kutusunu bul
        logo_div = soup.find('div', class_='elementor-widget-image')
        if logo_div:
            img_tag = logo_div.find('img')
            if img_tag:
                # Sırasıyla en iyi adayları kontrol et
                logo_url = (
                    img_tag.get('data-lazy-src') or 
                    img_tag.get('data-src') or 
                    img_tag.get('src')
                )
                # Eğer srcset varsa en yüksek çözünürlüklü olanı çekmeye çalış
                srcset = img_tag.get('srcset')
                if srcset and (not logo_url or 'data:image' in logo_url):
                    logo_url = srcset.split(',')[0].split(' ')[0]
        
        # Eksik URL'leri tamla
        if logo_url and not logo_url.startswith('http'):
            logo_url = urljoin(url, logo_url)

        # 3. Web URL
        web_url = ""
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            if "Web Sitesi" in cell.text:
                next_cell = cells[i+1]
                a_tag = next_cell.find('a')
                web_url = a_tag['href'] if a_tag else next_cell.text.strip()
                break
        
        if not web_url or "http" not in web_url: return None

        log(f"🏢 Bulundu: {unvan} | Logo: {'EVET' if logo_url else 'HAYIR'}")
        return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url}
    except: return None

def baslat():
    log("🚀 İSDER/İMDER Logo-Odaklı Tarama Başladı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    session = requests.Session()
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Ana Sayfa: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            # Uye linklerini topla
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/uye/' in href:
                    links.append(href)
            
            unique_links = list(set(links))
            log(f"📦 {len(unique_links)} firma incelenecek.")

            for link in unique_links:
                veri = detay_sayfasi_coz(link, session, headers)
                if veri:
                    status = airtable_ekle(veri)
                    if status in [200, 201]:
                        log(f"   ✅ {veri['firma_adi']} Airtable'a eklendi.")
                        processed_names.add(veri['firma_adi'])
                    time.sleep(1)
        except Exception as e:
            log(f"❌ Hata: {e}")

if __name__ == "__main__":
    baslat()
