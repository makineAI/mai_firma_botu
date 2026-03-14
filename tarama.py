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
    
    # Airtable 'Attachment' alanı için linki obje formatına çeviriyoruz
    logo_field = []
    if data.get("logo") and "http" in data.get("logo"):
        logo_field = [{"url": data.get("logo")}]

    payload = {
        "fields": {
            "firma_adi": str(data.get("firma_adi", ""))[:200],
            "web_url": str(data.get("web_url", "")),
            "logo": logo_field,  # Artık bir liste içinde obje!
            "hakkimizda": str(data.get("hakkimizda", ""))[:10000]
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return 200
        else:
            log(f"   ❌ Kayıt Hatası: {res.text}")
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
        # Sayfadaki tüm linkleri tara, içinde 'hakkımızda' geçenleri yakala
        for a in soup.find_all('a', href=True):
            text = a.text.lower()
            href = a['href'].lower()
            if any(k in text or k in href for k in ['hakkimizda', 'hakkinda', 'kurumsal', 'about', 'biz-kimiz']):
                link = a['href']
                h_link = link if "http" in link else firma_url.rstrip('/') + '/' + link.lstrip('/')
                break
        
        target_url = h_link if h_link else firma_url
        hr = requests.get(target_url, timeout=12, headers=headers, verify=False)
        hsoup = BeautifulSoup(hr.text, 'html.parser')
        # Sadece anlamlı paragrafları birleştir
        paragraflar = [p.text.strip() for p in hsoup.find_all(['p', 'div']) if len(p.text.strip()) > 60]
        text = " ".join(paragraflar[:10]) # İlk 10 anlamlı paragraf yeterli
        return text[:5000] if text else "İçerik bulunamadı."
    except:
        return "Firma sitesine ulaşılamadı veya içerik çekilemedi."

def detay_sayfasi_coz(url, session, headers):
    try:
        r = session.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Firma Ünvanı (Senin verdiğin h1 yapısı)
        unvan_tag = soup.find('h1', class_='elementor-heading-title')
        unvan = unvan_tag.text.strip() if unvan_tag else None
        
        if not unvan or unvan in processed_names: return None

        # Logo (Senin verdiğin img yapısı)
        logo = ""
        logo_div = soup.find('div', class_='elementor-widget-image')
        if logo_div and logo_div.find('img'):
            logo = logo_div.find('img').get('src')

        # Web URL (Tablo içindeki Web Sitesi satırı)
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
        # Gerçekten firmanın kendi sitesine gidip hakkımızda yazısını çekiyoruz
        hakkinda = firma_sitesinden_hakkinda_cek(web_url)

        return {
            "firma_adi": unvan,
            "web_url": web_url,
            "logo": logo,
            "hakkimizda": hakkinda
        }
    except: return None

def baslat():
    log("🚀 İSDER/İMDER Kesin Çözüm - Logo Fix")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    session = requests.Session()
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Tarama: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/uye/' in href or (ana_url.split('/')[2] in href and len(href.split('/')) > 4):
                    if not any(x in href for x in ['/category/', '/page/', '/tag/']):
                        links.append(href)
            
            for link in list(set(links)):
                veri = detay_sayfasi_coz(link, session, headers)
                if veri:
                    durum = airtable_ekle(veri)
                    if durum == 200:
                        log(f"   ✅ {veri['firma_adi']} kaydedildi.")
                        processed_names.add(veri['firma_adi'])
                    time.sleep(1)
        except Exception as e:
            log(f"❌ Hata: {e}")

if __name__ == "__main__":
    baslat()
