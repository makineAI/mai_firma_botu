import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

# SSL hatalarını görmezden gel
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIG / AYARLAR ---
# Bu değerlerin Airtable ile birebir aynı olması şarttır!
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    """Veriyi Airtable'a gönderir ve 422 hatası olursa detayını raporlar."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Airtable sütun isimleri burada belirleniyor. 
    # Tablonuzdaki sütun isimleri farklıysa bunları güncelleyin!
    fields = {
        "firma_adi": data.get("firma_adi", "Bilinmeyen Firma"),
        "web_url": data.get("web_url", ""),
        "platform": data.get("platform", ""),
        "kaynak_link": data.get("kaynak_link", "")
    }

    # Logo varsa ve geçerli bir URL ise ekle
    if data.get("logo") and data.get("logo").startswith("http"):
        fields["logo"] = [{"url": data.get("logo")}]

    payload = {"fields": fields}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return "✅ BAŞARILI"
        else:
            # 422 Hatası genelde buradaki print ile çözülür:
            print(f"❌ HATA ({res.status_code}): {res.text}")
            return f"HATA ({res.status_code})"
    except Exception as e:
        return f"Sistem Hatası: {e}"

def veri_ayikla(html, sayfa_url, platform_adi):
    """HTML'den veri çeker."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Firma Adı
    title_tag = soup.find('title')
    firma_adi = title_tag.get_text(strip=True).split('–')[0].strip() if title_tag else "İsimsiz"

    # Logo Bulucu (Elementor uyumlu)
    logo_url = ""
    img_tag = soup.select_one('.elementor-widget-image img')
    if img_tag:
        srcset = img_tag.get('srcset')
        logo_url = srcset.split(',')[-1].strip().split(' ')[0] if srcset else img_tag.get('src')

    # Link Temizleme (.webp ve boyut eklerini kaldır)
    if logo_url:
        logo_url = urljoin(sayfa_url, logo_url)
        # -300x127.png.webp -> .png formatına temizle
        logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('.webp')[0]

    # Web Sitesi URL
    web_url = ""
    for tr in soup.find_all('tr'):
        if any(x in tr.get_text() for x in ["Web Sitesi", "Web Site"]):
            a = tr.find('a', href=True)
            if a: web_url = a['href']
            break

    return {
        "firma_adi": firma_adi,
        "web_url": web_url,
        "logo": logo_url,
        "platform": platform_adi,
        "kaynak_link": sayfa_url
    }

def calistir():
    log("🚀 TARAMA BAŞLADI: İSDER & İMDER")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    siteler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in siteler:
        log(f"🔎 {hedef['platform']} taranıyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye linklerini topla (Sadece detay sayfaları)
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if hedef['platform'].lower() in href.lower() and len(href.split('/')) > 4:
                    if not any(x in href.lower() for x in ['haber', 'etkinlik', 'kurul', 'iletisim']):
                        links.add(urljoin(hedef["url"], href))

            for link in links:
                try:
                    res_detay = session.get(link, timeout=20, verify=False)
                    veri = veri_ayikla(res_detay.text, link, hedef['platform'])
                    
                    if veri and (veri['web_url'] or veri['logo']):
                        durum = airtable_ekle(veri)
                        log(f"{durum}: {veri['firma_adi']}")
                        time.sleep(0.5) # Airtable sınırı
                except:
                    continue
        except Exception as e:
            log(f"Hata oluştu: {e}")

if __name__ == "__main__":
    calistir()
