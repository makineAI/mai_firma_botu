import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3

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
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    # Airtable'ın reddetmemesi için veriyi temizle
    payload = {
        "fields": {
            "firma_adi": str(data.get("firma_adi", ""))[:200],
            "web_url": str(data.get("web_url", "")),
            "logo": str(data.get("logo", "")),
            "hakkimizda": str(data.get("hakkimizda", ""))[:10000] # Çok uzunsa kırp
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code not in [200, 201]:
            # Hatanın tam detayını görelim ki neyi beğenmediğini anlayalım
            log(f"   ❌ Detaylı Hata: {res.text}")
        return res.status_code
    except Exception as e:
        log(f"   ❌ Bağlantı Hatası: {e}")
        return 500

def firma_sitesinden_hakkinda_cek(firma_url):
    if not firma_url or "http" not in firma_url: return "Web sitesi bulunamadı."
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(firma_url, timeout=10, headers=headers, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        h_link = None
        for a in soup.find_all('a', href=True):
            if any(k in a.text.lower() for k in ['hakkımızda', 'kurumsal', 'hakkinda', 'about', 'biz kimiz']):
                link = a['href']
                h_link = link if "http" in link else firma_url.rstrip('/') + '/' + link.lstrip('/')
                break
        
        target_url = h_link if h_link else firma_url
        hr = requests.get(target_url, timeout=10, headers=headers, verify=False)
        hsoup = BeautifulSoup(hr.text, 'html.parser')
        paragraflar = [p.text.strip() for p in hsoup.find_all('p') if len(p.text.strip()) > 40]
        text = " ".join(paragraflar)
        return text[:5000] if text else "İçerik çekilemedi."
    except:
        return "Firma sitesine ulaşılamadı."

def detay_sayfasi_coz(url, session, headers):
    try:
        r = session.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Firma Ünvanı
        unvan_tag = soup.find('h1', class_='elementor-heading-title')
        unvan = unvan_tag.text.strip() if unvan_tag else None
        
        if not unvan or unvan in processed_names: return None

        # Logo
        logo = ""
        logo_div = soup.find('div', class_='elementor-widget-image')
        if logo_div and logo_div.find('img'):
            logo = logo_div.find('img').get('src')

        # Web URL
        web_url = ""
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            if "Web Sitesi" in cell.text:
                next_cell = cells[i+1]
                a_tag = next_cell.find('a')
                web_url = a_tag['href'] if a_tag else next_cell.text.strip()
                break
        
        if not web_url or "http" not in web_url: return None

        log(f"🏢 İşleniyor: {unvan}")
        hakkinda = firma_sitesinden_hakkinda_cek(web_url)

        return {
            "firma_adi": unvan,
            "web_url": web_url,
            "logo": logo,
            "hakkimizda": hakkinda
        }
    except: return None

def baslat():
    log("🚀 İSDER/İMDER Botu - Hata Giderme Modu")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    session = requests.Session()
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Tarama: {ana_url}")
        r = session.get(ana_url, headers=headers, timeout=20, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/uye/' in href or (ana_url.split('/')[2] in href and len(href.split('/')) > 4):
                if not any(x in href for x in ['/category/', '/page/', '/tag/']):
                    links.append(href)
        
        for link in list(set(links))[:30]: # Test için hızı artıralım
            veri = detay_sayfasi_coz(link, session, headers)
            if veri:
                durum = airtable_ekle(veri)
                if durum in [200, 201]:
                    log(f"   ✅ {veri['firma_adi']} kaydedildi.")
                    processed_names.add(veri['firma_adi'])
                time.sleep(1)

if __name__ == "__main__":
    baslat()
