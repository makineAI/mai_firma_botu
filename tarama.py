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
    
    # DİKKAT: Airtable'daki sütun isimlerin bunlarla BİREBİR aynı olmalı (Küçük/Büyük harf duyarlı)
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": [{"url": data.get("logo")}] if data.get("logo") else []
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def veri_ayikla(soup, link):
    # 1. H1 Başlık Kontrolü
    unvan = soup.select_one('h1.elementor-heading-title')
    if not unvan:
        # Alternatif başlık denemesi
        unvan = soup.select_one('h2')
    
    unvan_text = unvan.get_text(strip=True) if unvan else "Başlık Bulunamadı"
    
    # 2. Gereksiz sayfaları hızlıca ele
    if any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite', 'vizyon']):
        return None

    logo_url, web_url = "", ""
    
    # 3. Kapsayıcı Kontrolü
    inner_box = soup.select_one('.e-con-inner')
    if not inner_box:
        log(f"⚠️ {link} içinde '.e-con-inner' bulunamadı!")
        return None

    # Logo Bulucu
    img = inner_box.select_one('.elementor-widget-image img')
    if img:
        srcset = img.get('srcset')
        if srcset:
            logo_url = [p.strip().split(' ')[0] for p in srcset.split(',')][-1]
        else:
            logo_url = img.get('src') or img.get('data-src')
        
        if logo_url:
            logo_url = re.sub(r'-\d+x\d+', '', logo_url)

    # Web Sitesi Bulucu (Tabloyu tarar)
    for row in inner_box.find_all('tr'):
        text = row.get_text()
        if "Web Sitesi" in text or "Web" in text:
            a_tag = row.find('a')
            web_url = a_tag.get('href') if a_tag else row.find_all('td')[-1].get_text(strip=True)
            break

    if not web_url or "http" not in web_url:
        return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 OPERASYON: SON ŞANS")
    session = requests.Session()
    # Gerçek kullanıcı gibi görünmek için detaylı header
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "domain": "imder.org.tr"},
        {"url": "https://isder.org.tr/uyelerimiz/", "domain": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['domain']} listesi çekiliyor...")
        r = session.get(site["url"], timeout=30, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        links = {urljoin(site["url"], a['href']) for a in soup.find_all('a', href=True) 
                 if site["domain"] in a['href'] and len(a['href'].split('/')) > 4}

        log(f"📦 {len(links)} link bulundu. İşleme alınıyor...")

        for link in list(links)[:10]: # TEST İÇİN ŞİMDİLİK İLK 10 LİNK
            try:
                log(f"🔗 Sayfaya giriliyor: {link}")
                detay_r = session.get(link, timeout=15, verify=False)
                if detay_r.status_code != 200:
                    log(f"❌ Sayfa açılmadı: {detay_r.status_code}")
                    continue
                
                veri = veri_ayikla(BeautifulSoup(detay_r.text, 'html.parser'), link)
                if veri:
                    if veri["logo"] and not veri["logo"].startswith('http'):
                        veri["logo"] = urljoin(link, veri["logo"])
                    
                    status = airtable_ekle(veri)
                    log(f"✅ {veri['firma_adi']} -> Airtable: {status}")
                else:
                    log(f"❓ Veri ayıklanamadı: {link}")
                
                time.sleep(1) # Banlanmamak için şart
            except Exception as e:
                log(f"💥 Hata: {str(e)}")

if __name__ == "__main__":
    baslat()
