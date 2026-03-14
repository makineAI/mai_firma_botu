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
    
    # Airtable 'Attachment' alanı için format
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

def veri_ayikla(html, link):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Başlık Seçimi
    unvan = soup.select_one('h1.elementor-heading-title') or soup.select_one('h1')
    unvan_text = unvan.get_text(strip=True) if unvan else ""
    
    # SERT FİLTRE: Firma olmayan sayfaları içeriğe bakarak da ele
    yasakli_kelimeler = ['bülten', 'haber', 'duyuru', 'komite', 'başvuru', 'üyelik', 'etik', 'vizyon', 'iletisim']
    if not unvan_text or any(x in unvan_text.lower() for x in yasakli_kelimeler):
        return None

    logo_url, web_url = "", ""

    # 2. AGRESİF LOGO TEMİZLİĞİ
    images = soup.find_all('img')
    for img in images:
        src = ""
        srcset = img.get('srcset')
        if srcset:
            # En geniş resmi seç ve temizle
            src = [p.strip().split(' ')[0] for p in srcset.split(',')][-1]
        if not src:
            src = img.get('data-src') or img.get('src')
        
        if src and any(x in src.lower() for x in ['logo', 'member', 'uye', 'uploads']):
            logo_url = urljoin(link, src)
            # WordPress'in eklediği -300x300 gibi boyutları SİL (Airtable orijinali sever)
            logo_url = re.sub(r'-\d+x\d+', '', logo_url)
            # Varsa .webp sonrasındaki parametreleri temizle
            logo_url = logo_url.split('?')[0]
            break

    # 3. WEB URL (Tablo içinde "Web Sitesi" yazan yer)
    for row in soup.find_all('tr'):
        if "Web Sitesi" in row.get_text():
            a = row.find('a')
            if a: web_url = a.get('href')
            break

    if not web_url: return None
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 AYIKLANMIŞ VE LOGO ODAKLI TARAMA")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'})

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "domain": "imder.org.tr"},
        {"url": "https://isder.org.tr/uyelerimiz/", "domain": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['domain']} taranıyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # LİNK FİLTRESİ: Basın bülteni ve kurumsal sayfaları en baştan at
            links = set()
            for a in soup.find_all('a', href=True):
                h = a['href']
                # Firma detay sayfaları genellikle 3-4 kırılımlı linklerdir
                if site["domain"] in h and len(h.strip('/').split('/')) >= 3:
                    if not any(x in h.lower() for x in ['haberler', 'bulten', 'basin', 'etik', 'komite', 'uye-ol', 'iletisim']):
                        links.add(urljoin(site["url"], h))

            for link in links:
                try:
                    detay_r = session.get(link, timeout=15, verify=False)
                    veri = veri_ayikla(detay_r.text, link)
                    if veri:
                        status = airtable_ekle(veri)
                        log(f"✅ {veri['firma_adi']} | Logo: {'EVET' if veri['logo'] else 'HAYIR'} | Airtable: {status}")
                        time.sleep(1) # Airtable hız limiti koruması
                except: continue
        except Exception as e: log(f"💥 Hata: {e}")

if __name__ == "__main__":
    baslat()
