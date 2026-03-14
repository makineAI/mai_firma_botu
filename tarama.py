import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import urllib3
from urllib.parse import urljoin

# SSL uyarılarını kapatıp logları temiz tutalım
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    
    # Airtable 'Attachment' (Ek) alanı için özel format
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

def veri_ayikla(soup):
    # 1. FIRMA ADI (H1 her zaman ana başlıktır)
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    
    # Gereksiz sayfaları (Kurumsal sayfalar vb.) filtrele
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']):
        return None

    # 2. SENİN VERDİĞİN VERİNİN OLDUĞU ANA KUTU (.e-con-inner)
    inner_box = soup.select_one('.e-con-inner')
    if not inner_box: return None

    logo_url = ""
    web_url = ""
    
    # --- LOGO AVCI ---
    # inner_box içindeki resim kutusuna odaklan
    img = inner_box.select_one('.elementor-widget-image img')
    if img:
        # Öncelik: srcset (Senin verdiğin kodda yüksek kaliteli linkler burada)
        srcset = img.get('srcset')
        if srcset:
            logo_url = srcset.split(',')[0].split(' ')[0].strip()
        # Eğer srcset yoksa src veya data-src bak
        if not logo_url or "data:image" in logo_url:
            logo_url = img.get('src') or img.get('data-src')

    # --- WEB URL AVCI ---
    # Tablo satırlarını tara, "Web Sitesi" yazan satırı bul
    rows = inner_box.find_all('tr')
    for row in rows:
        row_text = row.get_text()
        if "Web Sitesi" in row_text:
            a_tag = row.find('a')
            if a_tag:
                web_url = a_tag.get('href')
            else:
                # Link yoksa td içindeki düz metni al
                tds = row.find_all('td')
                if len(tds) > 1:
                    web_url = tds[1].get_text(strip=True)
            break

    # Kritik veri (web_url) yoksa Airtable'a boş veri gönderme
    if not web_url or "http" not in web_url:
        return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 LOGO VE WEB URL ODAKLI SAF TARAMA BAŞLADI")
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "domain": "imder.org.tr"},
        {"url": "https://isder.org.tr/uyelerimiz/", "domain": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['domain'].upper()} taranıyor...")
        try:
            r = session.get(site["url"], headers=headers, timeout=20, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Detay linklerini ayıkla
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                if site["domain"] in h and len(h.split('/')) > 4:
                    if not any(x in h.lower() for x in ['page', 'etik', 'komite', 'uyelik']):
                        links.add(h)

            log(f"📦 {len(links)} firma linki bulundu.")

            for link in links:
                try:
                    detay_r = session.get(link, headers=headers, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    veri = veri_ayikla(detay_soup)
                    
                    if veri:
                        # Göreceli linkleri tam adrese çevir
                        if veri["logo"] and not veri["logo"].startswith('http'):
                            veri["logo"] = urljoin(link, veri["logo"])
                        
                        status = airtable_ekle(veri)
                        log(f"   🏢 {veri['firma_adi']} | Logo: {'✅' if veri['logo'] else '❌'} | Airtable: {status}")
                        time.sleep(1) # Airtable hız limiti koruması
                except: continue
        except Exception as e:
            log(f"❌ Hata: {e}")

if __name__ == "__main__":
    baslat()
