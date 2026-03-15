import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

# SSL uyarılarını sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    """Veriyi Airtable'a gönderir."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    fields = {
        "firma_adi": data.get("firma_adi"),
        "web_url": data.get("web_url"),
        "platform": data.get("platform")
    }

    # Logo (Airtable Attachment formatında)
    if data.get("logo"):
        fields["logo"] = [{"url": data.get("logo")}]

    payload = {"fields": fields}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return "✅" if res.status_code in [200, 201] else f"❌ ({res.status_code})"
    except:
        return "⚠️"

def veri_ayikla(html, sayfa_url, platform_adi):
    """Paylaştığın özel HTML yapısından veriyi çeker."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Firma Ünvanı (Sayfa başlığından veya tablodan bağımsız en temiz hali)
    # Genelde title etiketi firma adını içerir
    title_tag = soup.find('title')
    unvan = title_tag.get_text().split('–')[0].split('|')[0].strip() if title_tag else "Bilinmeyen"

    # 🛑 KRİTİK FİLTRE: Eğer sayfa firma sayfası değilse (Üyelik, Etik vs.) ATLA
    yasakli = ["etik", "üyelik", "form", "kayıt", "hakkımızda", "tüzük", "vizyon"]
    if any(x in unvan.lower() for x in yasakli):
        return None

    # 2. Logo (Verdiğin elementor-widget-image içindeki en büyük görsel)
    logo_url = ""
    img_tag = soup.select_one('.elementor-widget-image img')
    if img_tag:
        srcset = img_tag.get('srcset')
        if srcset:
            # En sondaki/en büyük görseli al
            logo_url = srcset.split(',')[-1].strip().split(' ')[0]
        else:
            logo_url = img_tag.get('src')
        
        # WebP ve boyut temizliği
        logo_url = urljoin(sayfa_url, logo_url)
        logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('.webp')[0]

    # 3. Web Sitesi (Tablodaki 'Web Sitesi' satırından çek)
    web_url = ""
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 2:
            key = tds[0].get_text(strip=True).lower()
            if "web" in key:
                a_tag = tds[1].find('a', href=True)
                web_url = a_tag['href'] if a_tag else tds[1].get_text(strip=True)
                break
    
    # Web URL hala bulunamadıysa (Alternatif arama)
    if not web_url or "http" not in web_url:
        for a in soup.find_all('a', href=True):
            href = a['href']
            if "http" in href and not any(x in href for x in ['isder', 'imder', 'facebook', 'instagram', 'linkedin', 'twitter']):
                web_url = href
                break

    # 🛑 Web sitesi yoksa yine de alma (Çöp veriyi engeller)
    if not web_url or len(web_url) < 5:
        return None

    return {
        "firma_adi": unvan,
        "web_url": web_url,
        "logo": logo_url,
        "platform": platform_adi
    }

def baslat():
    log("🚀 İSADER & İMADER NOKTA ATIŞI TARAMA")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    hedefler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in hedefler:
        log(f"🔎 {hedef['platform']} Listesi taranıyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Tüm üye linklerini topla
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if f"/{hedef['platform'].lower()}/" in href.lower() and len(href.split('/')) > 4:
                    if not any(x in href.lower() for x in ['haber', 'etik', 'iletisim', 'bulten']):
                        links.add(urljoin(hedef["url"], href))

            for link in links:
                try:
                    res_detay = session.get(link, timeout=15, verify=False)
                    veri = veri_ayikla(res_detay.text, link, hedef['platform'])
                    
                    if veri:
                        durum = airtable_ekle(veri)
                        log(f"{durum} {veri['firma_adi']} ({hedef['platform']})")
                        time.sleep(0.4)
                except: continue
        except Exception as e:
            log(f"Hata: {e}")

if __name__ == "__main__":
    baslat()
