import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    """Veriyi sadece firma_adi, web_url, platform ve logo sütunlarına gönderir."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Senin belirttiğin sütun isimleriyle birebir eşleşen yapı
    fields = {
        "firma_adi": data.get("firma_adi", "Bilinmeyen Firma"),
        "web_url": data.get("web_url", ""),
        "platform": data.get("platform", "")
    }

    # Logo varsa ve geçerli bir linkse ekle
    if data.get("logo") and data.get("logo").startswith("http"):
        fields["logo"] = [{"url": data.get("logo")}]

    payload = {"fields": fields}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return "✅ BAŞARILI"
        else:
            # Hata devam ederse detayını burada göreceğiz
            print(f"❌ HATA ({res.status_code}): {res.text}")
            return f"HATA ({res.status_code})"
    except Exception as e:
        return f"Bağlantı Hatası: {e}"

def veri_ayikla(html, sayfa_url, platform_adi):
    """HTML içinden logoyu ve firma bilgilerini ayıklar."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Firma Adı
    title_tag = soup.find('title')
    firma_adi = title_tag.get_text(strip=True).split('–')[0].strip() if title_tag else "İsimsiz"

    # 2. Logo Bulucu (İMDER/İSDER Elementor yapısı)
    logo_url = ""
    img_tag = soup.select_one('.elementor-widget-image img')
    if img_tag:
        srcset = img_tag.get('srcset')
        if srcset:
            # En yüksek çözünürlüklü versiyonu al
            logo_url = srcset.split(',')[-1].strip().split(' ')[0]
        else:
            logo_url = img_tag.get('src')

    # 3. Logo URL Temizliği (Boyut eklerini ve .webp formatını temizler)
    if logo_url:
        logo_url = urljoin(sayfa_url, logo_url)
        # Örn: -300x127.png.webp -> .png yapar
        logo_url = re.sub(r'-\d+x\d+', '', logo_url).split('.webp')[0]

    # 4. Firma Web Sitesi
    web_url = ""
    for tr in soup.find_all('tr'):
        text = tr.get_text()
        if "Web Sitesi" in text or "Web Site" in text:
            a = tr.find('a', href=True)
            if a: 
                web_url = a['href']
                break

    return {
        "firma_adi": firma_adi,
        "web_url": web_url,
        "logo": logo_url,
        "platform": platform_adi
    }

def baslat():
    log("🚀 TARAMA VE AKTARIM BAŞLATILDI")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    hedefler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in hedefler:
        log(f"🔎 {hedef['platform']} üyeleri taranıyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye sayfalarının linklerini ayıkla
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Linkin içinde platform adı geçiyor mu ve yeterince derin mi?
                if f"/{hedef['platform'].lower()}" in href.lower() and len(href.split('/')) > 4:
                    # Filtreleme: Gereksiz sayfaları atla
                    if not any(x in href.lower() for x in ['haber', 'etkinlik', 'iletisim', 'bulten', 'kvkk']):
                        links.add(urljoin(hedef["url"], href))

            log(f"📦 {len(links)} firma bulundu. Veriler Airtable'a gönderiliyor...")

            for link in links:
                try:
                    res_detay = session.get(link, timeout=20, verify=False)
                    veri = veri_ayikla(res_detay.text, link, hedef['platform'])
                    
                    if veri:
                        durum = airtable_ekle(veri)
                        log(f"{durum}: {veri['firma_adi']}")
                        time.sleep(0.5) # Airtable hız limiti (Rate limit)
                except Exception as e:
                    continue

        except Exception as e:
            log(f"⚠️ {hedef['platform']} taranırken ana hata: {e}")

if __name__ == "__main__":
    baslat()
