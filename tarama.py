import requests
from bs4 import BeautifulSoup
import os
import sys
import time

# Airtable Bilgileri
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    res = requests.post(url, json={"fields": data}, headers=headers)
    return res.status_code

def tarayici_simulasyonu(url):
    # Gerçek bir insan tarayıcısı başlıkları (Headers)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    }
    
    session = requests.Session()
    try:
        # Önce ana sayfaya git (Engel varsa burada belli olur)
        log(f"Siteye giriliyor: {url}")
        response = session.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code != 200:
            log(f"❌ ENGEL! Site hata kodu verdi: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sitedeki tüm linkleri bul
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Eğer link dernek sitesinin içindeyse ve bir üye sayfasına benziyorsa
            if ('isder.org.tr' in href or 'imder.org.tr' in href) and len(href.split('/')) > 4:
                if not any(x in href for x in ['/category/', '/page/', '/tag/', '/iletisim/']):
                    links.append(href)
        
        links = list(set(links))
        log(f"✅ {len(links)} adet firma linki tespit edildi.")

        for link in links:
            try:
                log(f"📄 Firma Detay: {link}")
                r_detay = session.get(link, headers=headers, timeout=15, verify=False)
                s_detay = BeautifulSoup(r_detay.text, 'html.parser')
                
                unvan = s_detay.find('h1').text.strip() if s_detay.find('h1') else None
                if not unvan: continue

                # Web sitesini bul (Dış link)
                web_tag = s_detay.find('a', href=lambda x: x and 'http' in x and 'isder' not in x and 'imder' not in x and 'facebook' not in x and 'linkedin' not in x)
                
                if web_tag:
                    web_url = web_tag['href'].strip('/')
                    log(f"   🏢 {unvan} -> {web_url}")
                    
                    # Airtable'a gönder
                    durum = airtable_ekle({
                        "firma_adi": unvan,
                        "web_url": web_url,
                        "hakkimizda": "Detaylar taranacak..." # Önce isimleri alalım
                    })
                    if durum in [200, 201]:
                        log(f"   ✨ Airtable'a kaydedildi.")
                    else:
                        log(f"   ⚠️ Airtable kayıt hatası: {durum}")
                
                time.sleep(2) # Engellenmemek için bekle
            except:
                continue

    except Exception as e:
        log(f"❌ Bağlantı koptu: {e}")

if __name__ == "__main__":
    log("🚀 İSDER/İMDER Tarama Başladı")
    siteler = ["https://isder.org.tr/uyelerimiz/", "https://imder.org.tr/uyelerimiz/"]
    for s in siteler:
        tarayici_simulasyonu(s)
    log("🏁 İşlem Tamam.")
