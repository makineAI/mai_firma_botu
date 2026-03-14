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

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    # Airtable .webp dosyalarını bazen doğrudan kabul etmez, 
    # bu yüzden sadece URL olarak da kaydedelim (Yedek plan)
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": [{"url": data.get("logo")}] if data.get("logo") else []
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code not in [200, 201]:
            log(f"   ⚠️ Airtable Hatası: {res.text}")
        return res.status_code
    except Exception as e:
        log(f"   ⚠️ İstek Hatası: {e}")
        return 500

def detay_sayfasi_coz(url, session, headers):
    try:
        r = session.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # FIRMA ADI
        unvan = soup.select_one('h1.elementor-heading-title')
        unvan = unvan.get_text(strip=True) if unvan else None
        if not unvan or "Üyelik" in unvan or "Etik" in unvan: return None

        # LOGO - EN AGRESİF ARAMA
        logo_url = ""
        # Senin verdiğin nokta atışı: elementor-widget-image içindeki ilk img
        img = soup.select_one('.elementor-widget-image img')
        if img:
            # 1. Seçenek: srcset içindeki en büyük resmi bulalım
            srcset = img.get('srcset')
            if srcset:
                # Virgülle ayrılmış listeyi temizle ve son (genelde en büyük) linki al
                links = [s.strip().split(' ')[0] for s in srcset.split(',')]
                logo_url = links[-1] # Listenin sonundaki genelde en kalitelisidir
            # 2. Seçenek: data-src veya src
            if not logo_url or "data:image" in logo_url:
                logo_url = img.get('src') or img.get('data-src')

        # WEB URL
        web_url = ""
        for row in soup.find_all('tr'):
            if "Web Sitesi" in row.get_text():
                a = row.find('a')
                web_url = a['href'] if a else row.find_all('td')[-1].get_text(strip=True)
                break

        if not web_url or "http" not in web_url: return None

        log(f"🏢 {unvan} | Logo Bulundu mu?: {'EVET' if logo_url else 'HAYIR'}")
        if logo_url: log(f"   🖼️ Logo Linki: {logo_url[:50]}...")
        
        return {"firma_adi": unvan, "web_url": web_url, "logo": logo_url}
    except: return None

def baslat():
    log("🚀 LOGO GARANTİLİ Tarama Başladı")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
    session = requests.Session()
    
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    
    for ana_url in siteler:
        log(f"🔗 Ana Sayfa: {ana_url}")
        r = session.get(ana_url, headers=headers, timeout=20, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Linkleri topla
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if ana_url in href and len(href.split('/')) > 4:
                if not any(x in href for x in ['page', 'etik', 'komite']):
                    links.add(href)

        for link in links:
            veri = detay_sayfasi_coz(link, session, headers)
            if veri:
                airtable_ekle(veri)
                time.sleep(1)

if __name__ == "__main__":
    baslat()
