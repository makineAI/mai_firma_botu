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
        
        # 1. FIRMA UNVANI (Nokta Atışı)
        unvan_tag = soup.select_one('h1.elementor-heading-title')
        unvan = unvan_tag.get_text(strip=True) if unvan_tag else None
        if not unvan or unvan in processed_names: return None

        # 2. LOGO (Nokta Atışı - img srcset ve src kontrolü)
        logo_url = ""
        # elementor-widget-image içindeki img etiketine bak
        img_tag = soup.select_one('.elementor-widget-image img')
        if img_tag:
            # Önce srcset (çünkü Elementor asıl resmi burada tutuyor olabilir)
            srcset = img_tag.get('srcset')
            if srcset:
                # En yüksek çözünürlüklü olanı veya ilkini al
                logo_url = srcset.split(',')[0].split(' ')[0]
            else:
                # srcset yoksa normal src veya lazy-load src'lere bak
                logo_url = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')

        # 3. WEB URL (Nokta Atışı - Tablo hücresi kontrolü)
        web_url = ""
        # Sayfadaki tüm <tr> etiketlerini gez
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            if len(tds) >= 2:
                # Eğer ilk td "Web Sitesi" yazısını içeriyorsa
                if "Web Sitesi" in tds[0].get_text():
                    # İkinci td'nin içindeki <a> etiketini veya direkt metni al
                    a_link = tds[1].find('a')
                    web_url = a_link.get('href') if a_link else tds[1].get_text(strip=True)
                    break
        
        # URL temizliği (Eğer sadece metin gelmişse ve http içermiyorsa başına ekle)
        if web_url and not web_url.startswith('http'):
            web_url = "http://" + web_url.replace(" ", "")

        if not unvan: return None

        log(f"🏢 İşleniyor: {unvan} | Web: {web_url[:30]}... | Logo: {'OK' if logo_url else 'YOK'}")
        return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url}
    except Exception as e:
        log(f"   ⚠️ Hata: {str(e)}")
        return None

def baslat():
    log("🚀 NOKTA ATISI Tarama Başlatıldı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    session = requests.Session()
    
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Ana Sayfa: {ana_url}")
        try:
            r = session.get(ana_url, headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye profil linklerini bulmak için genel tarama
            links = []
            for a in soup.find_all('a', href=True):
                h = a['href']
                # Linkin içinde /uyelerimiz/ yoksa ama ana site adı varsa ve derinlik fazlaysa
                if ana_url in h and h != ana_url:
                    links.append(h)
                elif (h.startswith('https://isder.org.tr/') or h.startswith('https://imder.org.tr/')) and len(h.split('/')) > 4:
                    if not any(x in h for x in ['/category/', '/tag/', '/page/', '/wp-content/']):
                        links.append(h)

            unique_links = list(set(links))
            log(f"📦 {len(unique_links)} firma bulundu.")

            for link in unique_links:
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
