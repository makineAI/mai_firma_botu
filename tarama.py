import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

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
    
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": [{"url": data.get("logo")}] if data.get("logo") else [],
            "platform": data.get("platform")
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def detay_sayfadan_web_bul(html):
    """Sadece iç sayfadaki web sitesi linkini söker."""
    soup = BeautifulSoup(html, 'html.parser')
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a = row.find('a')
            if a: return a.get('href')
    return None

def baslat():
    log("🚀 KART TABANLI LOGO OPERASYONU BAŞLADI")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'})

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "imder"},
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "isder"}
    ]

    for site in siteler:
        log(f"🔎 {site['platform'].upper()} listesi taranıyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Kartları bulalım (Gönderdiğin article yapısı)
            kartlar = soup.select('article.elementor-post')
            log(f"📦 {len(kartlar)} firma kartı bulundu.")

            for kart in kartlar:
                try:
                    # 1. LOGO YAKALAMA (Kartın içindeki görsel)
                    img_tag = kart.select_one('.elementor-post__thumbnail img')
                    logo_url = ""
                    if img_tag:
                        srcset = img_tag.get('srcset')
                        if srcset:
                            logo_url = [p.strip().split(' ')[0] for p in srcset.split(',')][-1]
                        else:
                            logo_url = img_tag.get('src')
                        
                        # Temizlik
                        logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('?')[0]

                    # 2. DETAY LİNKİ VE FİRMA ADI
                    link_tag = kart.select_one('a.elementor-post__thumbnail__link')
                    detay_link = link_tag.get('href') if link_tag else None
                    
                    if not detay_link: continue

                    # 3. İÇ SAYFAYA SADECE WEB URL İÇİN GİRİŞ
                    detay_r = session.get(detay_link, timeout=15, verify=False)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    
                    # Firma Adı (İç sayfadan daha temiz gelir)
                    unvan = detay_soup.select_one('h1.elementor-heading-title') or detay_soup.select_one('h1')
                    firma_adi = unvan.get_text(strip=True) if unvan else "İsimsiz Firma"

                    web_url = detay_sayfadan_web_bul(detay_r.text)
                    
                    if web_url and firma_adi:
                        veri = {
                            "firma_adi": firma_adi,
                            "web_url": web_url,
                            "logo": logo_url,
                            "platform": site['platform']
                        }
                        status = airtable_ekle(veri)
                        log(f"✅ [{site['platform']}] {firma_adi} | Logo: {'OK' if logo_url else 'HAYIR'} | Airtable: {status}")
                        time.sleep(1)
                except Exception as e:
                    continue
        except Exception as e:
            log(f"💥 Liste Hatası: {e}")

if __name__ == "__main__":
    baslat()
