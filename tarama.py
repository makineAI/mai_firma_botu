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
            "logo": [{"url": data.get("logo")}] if data.get("logo") else []
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except: return 500

def veri_ayikla(html, link):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Başlık: H1 yoksa Title'dan al (Daha garantidir)
    unvan = soup.select_one('h1.elementor-heading-title') or soup.select_one('h1')
    unvan_text = unvan.get_text(strip=True) if unvan else soup.title.string.split('|')[0].strip()
    
    if any(x in unvan_text.lower() for x in ['başvurusu', 'iletisim', 'uyelerimiz']): return None

    logo_url, web_url = "", ""

    # 2. LOGO: Sayfadaki en büyük resmi veya 'logo' geçen ilk resmi bul
    images = soup.find_all('img')
    for img in images:
        src = img.get('srcset', '').split(' ')[0] or img.get('src') or img.get('data-src')
        if src and any(x in src.lower() for x in ['logo', 'member', 'uye']):
            logo_url = urljoin(link, src)
            break

    # 3. WEB URL: 'http' içeren ve firma ismiyle eşleşmeyen dış linkleri tara
    # Tabloyu bulamazsa bile a etiketlerinden ayıklamaya çalışır
    links = soup.find_all('a', href=True)
    for a in links:
        href = a['href']
        if "http" in href and not any(x in href for x in ['imder.org.tr', 'isder.org.tr', 'facebook', 'linkedin', 'instagram', 'twitter']):
            web_url = href
            break

    if not web_url: return None
    
    # Logo URL temizliği
    if logo_url: logo_url = re.sub(r'-\d+x\d+', '', logo_url)

    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}

def baslat():
    log("🚀 OPERASYON: RADİKAL ÇÖZÜM")
    session = requests.Session()
    # EN ÜST SEVİYE HEADER (Tarayıcı taklidi)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    })

    siteler = [
        {"url": "https://imder.org.tr/uyelerimiz/", "domain": "imder.org.tr"},
        {"url": "https://isder.org.tr/uyelerimiz/", "domain": "isder.org.tr"}
    ]

    for site in siteler:
        log(f"🔎 {site['domain']} ana listesi çekiliyor...")
        try:
            r = session.get(site["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Sadece firma olabilecek linkleri filtrele (link sonu / ile bitenler genelde firmadır)
            links = {urljoin(site["url"], a['href']) for a in soup.find_all('a', href=True) 
                     if site["domain"] in a['href'] and len(a['href'].strip('/').split('/')) >= 3}

            for link in links:
                if any(x in link for x in ['/page/', '/etik-', '/komite', '/uyelik', '/mavi-yaka', '/beyaz-yaka', '/iletisim', '/uyelerimiz/']): continue
                
                try:
                    log(f"🔗 Giriliyor: {link}")
                    detay_r = session.get(link, timeout=15, verify=False)
                    if "cloudflare" in detay_r.text.lower():
                        log("⚠️ Cloudflare engeline takıldık!")
                        continue
                    
                    veri = veri_ayikla(detay_r.text, link)
                    if veri:
                        status = airtable_ekle(veri)
                        log(f"✅ {veri['firma_adi']} -> Airtable: {status}")
                    else:
                        log(f"❌ Veri boş: {link}")
                    
                    time.sleep(2) # Engellenmemek için süreyi artırdık
                except: continue
        except Exception as e:
            log(f"💥 Ana hata: {e}")

if __name__ == "__main__":
    baslat()
