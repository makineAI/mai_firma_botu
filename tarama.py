import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Airtable Bilgileri
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

processed_names = set() # Mükerrer firma ünvanı kontrolü

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"fields": data}, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def firma_sitesinden_hakkinda_cek(firma_url):
    """Firmanın kendi sitesine gidip hakkımızda yazısını çeker."""
    if not firma_url or "http" not in firma_url: return "Web sitesi bulunamadı."
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(firma_url, timeout=10, headers=headers, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Hakkımızda/Kurumsal linkini ara
        h_link = None
        for a in soup.find_all('a', href=True):
            if any(k in a.text.lower() for k in ['hakkımızda', 'kurumsal', 'hakkinda', 'about']):
                link = a['href']
                h_link = link if "http" in link else firma_url.rstrip('/') + '/' + link.lstrip('/')
                break
        
        target_url = h_link if h_link else firma_url
        hr = requests.get(target_url, timeout=10, headers=headers, verify=False)
        hsoup = BeautifulSoup(hr.text, 'html.parser')
        paragraflar = [p.text.strip() for p in hsoup.find_all('p') if len(p.text.strip()) > 40]
        text = " ".join(paragraflar)
        return text[:1500] + "..." if text else "İçerik çekilemedi."
    except:
        return "Firma sitesine ulaşılamadı."

def detay_sayfasi_coz(url, session, headers):
    """Verdiğin HTML yapısına göre detay sayfasını kazır."""
    try:
        r = session.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Firma Ünvanı (h1.elementor-heading-title)
        unvan_tag = soup.find('h1', class_='elementor-heading-title')
        unvan = unvan_tag.text.strip() if unvan_tag else None
        
        if not unvan or unvan in processed_names:
            return None # Mükerrer veya boşsa geç

        # 2. Logo (img içindeki src)
        logo = "Bulunamadı"
        # elementor-widget-image içindeki ilk resmi al
        logo_div = soup.find('div', class_='elementor-widget-image')
        if logo_div and logo_div.find('img'):
            logo = logo_div.find('img').get('src')

        # 3. Web URL (Tablo içindeki Web Sitesi satırı)
        web_url = "Bulunamadı"
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            if "Web Sitesi" in cell.text:
                # Bir sonraki td hücresindeki linki veya metni al
                next_cell = cells[i+1]
                a_tag = next_cell.find('a')
                web_url = a_tag['href'] if a_tag else next_cell.text.strip()
                break
        
        if web_url == "Bulunamadı": return None # Web sitesi yoksa veri eksiktir

        log(f"🏢 İşleniyor: {unvan}")
        hakkinda = firma_sitesinden_hakkinda_cek(web_url)

        return {
            "firma_adi": unvan,
            "web_url": web_url,
            "logo": logo,
            "hakkimizda": hakkinda
        }
    except Exception as e:
        log(f"⚠️ Detay çekme hatası: {e}")
        return None

def baslat():
    log("🚀 İSDER/İMDER Kesin Çözüm Botu Başladı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    session = requests.Session()
    
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Ana sayfa taranıyor: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye linklerini bul (Genelde h3 veya a etiketlerinde profil linkleri olur)
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/uye/' in href or (ana_url.split('/')[2] in href and len(href.split('/')) > 4):
                    if not any(x in href for x in ['/category/', '/page/', '/tag/', '/iletisim/']):
                        links.append(href)
            
            links = list(set(links))
            log(f"📦 {len(links)} firma linki bulundu. Derin tarama başlıyor...")

            for link in links:
                veri = detay_sayfasi_coz(link, session, headers)
                if veri:
                    durum = airtable_ekle(veri)
                    if durum in [200, 201]:
                        log(f"   ✅ {veri['firma_adi']} Airtable'a eklendi.")
                        processed_names.add(veri['firma_adi'])
                    else:
                        log(f"   ❌ Airtable Hatası: {durum}")
                time.sleep(1) # IP ban yememek için
                
        except Exception as e:
            log(f"❌ Ana sayfa hatası: {e}")

if __name__ == "__main__":
    baslat()
    log("🏁 İşlem başarıyla tamamlandı.")
