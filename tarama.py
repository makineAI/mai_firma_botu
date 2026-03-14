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
    
    # Airtable Attachment formatı (Logo için)
    logo_field = [{"url": data.get("logo")}] if data.get("logo") and "http" in data.get("logo") else []

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
        
        # 1. FIRMA UNVANI (Senin attığın h1 yapısı)
        # <h1 class="elementor-heading-title elementor-size-default">
        unvan_tag = soup.find('h1', class_='elementor-heading-title')
        unvan = unvan_tag.get_text(strip=True) if unvan_tag else None
        
        if not unvan or unvan in processed_names: return None

        # 2. LOGO (Senin attığın img yapısı)
        # elementor-widget-image içindeki img
        logo_url = ""
        logo_div = soup.find('div', class_='elementor-widget-image')
        if logo_div and logo_div.find('img'):
            img_tag = logo_div.find('img')
            # Srcset varsa en büyüğünü, yoksa src'yi al
            logo_url = img_tag.get('src')
            if img_tag.get('srcset'):
                logo_url = img_tag.get('srcset').split(',')[0].split(' ')[0]
        
        if logo_url and not logo_url.startswith('http'):
            logo_url = urljoin(url, logo_url)

        # 3. WEB URL (Senin attığın tablo yapısı)
        # <tr><td><strong>Web Sitesi:</strong></td><td>...</td></tr>
        web_url = ""
        # Sayfadaki tüm güçlü (strong) metinleri tara
        for strong in soup.find_all('strong'):
            if "Web Sitesi" in strong.get_text():
                # td -> td yapısında yan hücreye bak
                parent_td = strong.find_parent('td')
                if parent_td:
                    next_td = parent_td.find_next_sibling('td')
                    if next_td:
                        a_tag = next_td.find('a')
                        web_url = a_tag['href'] if a_tag else next_td.get_text(strip=True)
                break
        
        if not web_url or "http" not in web_url: return None

        log(f"🏢 İşleniyor: {unvan}")
        return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url}
    except Exception as e:
        return None

def baslat():
    log("🚀 İSDER/İMDER Tarama Başlatıldı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    session = requests.Session()
    
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Ana Sayfa taranıyor: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Link toplama mantığını genişletiyoruz
            # Sitedeki tüm a etiketlerini bul, içinde /uyelerimiz/ dışında olan profil linklerini yakala
            all_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Link ana URL ile başlıyorsa ve sadece ana sayfa değilse (derinlik varsa)
                if ana_url in href and href != ana_url:
                    all_links.append(href)
                # Alternatif: Kısa link yapısı (isder.org.tr/firma-adi)
                elif href.startswith('https://isder.org.tr/') or href.startswith('https://imder.org.tr/'):
                    if len(href.split('/')) > 4: # Belli bir derinlikteki linkler genelde profildir
                        all_links.append(href)

            unique_links = list(set(all_links))
            log(f"📦 {len(unique_links)} potansiyel firma linki bulundu.")

            for link in unique_links:
                if any(x in link for x in ['/category/', '/tag/', '/page/', '/wp-content/']): continue
                
                veri = detay_sayfasi_coz(link, session, headers)
                if veri:
                    status = airtable_ekle(veri)
                    if status in [200, 201]:
                        log(f"   ✅ {veri['firma_adi']} kaydedildi.")
                        processed_names.add(veri['firma_adi'])
                    time.sleep(1)
        except Exception as e:
            log(f"❌ Ana sayfa hatası: {e}")

if __name__ == "__main__":
    baslat()
