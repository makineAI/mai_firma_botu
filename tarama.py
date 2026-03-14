import requests
from bs4 import BeautifulSoup
import os, sys, time, urllib3, re
from urllib.parse import urljoin

# SSL sertifika uyarılarını kapat (Dernek sitelerinde sorun olabiliyor)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
# GitHub Secrets veya Environment Variables üzerinden gelmeli
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def log(msg):
    """Terminalde süreci takip etmek için."""
    print(f">>> {msg}")
    sys.stdout.flush()

def airtable_ekle(data):
    """Veriyi Airtable'a gönderir."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": {
            "firma_adi": data.get("firma_adi"),
            "web_url": data.get("web_url"),
            "logo": [{"url": data.get("logo")}] if data.get("logo") else [],
            "platform": data.get("platform"),
            "kaynak_link": data.get("kaynak_link")
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return res.status_code
    except Exception as e:
        return f"Hata: {e}"

def veri_ayikla(html, sayfa_url, platform_adi):
    """HTML yapısından firma bilgilerini ve logoyu çeker."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Firma Adı (Title'dan temizle)
    title_tag = soup.find('title')
    firma_adi = title_tag.get_text(strip=True).split('–')[0].strip() if title_tag else ""

    # 2. Logo Avcısı (Elementor Widget Yapısı)
    logo_url = ""
    # Paylaştığın kodda 'elementor-widget-image' içinde img etiketi var
    img_container = soup.select_one('.elementor-widget-image img')
    
    if img_container:
        # Önce srcset (yüksek çözünürlük için), yoksa src al
        srcset = img_container.get('srcset')
        if srcset:
            # En sondaki (genelde en büyük) linki al
            logo_url = srcset.split(',')[-1].strip().split(' ')[0]
        else:
            logo_url = img_container.get('src')

    # 3. Logo Linkini Temizleme (WebP ve Boyut sorunlarını çözer)
    if logo_url:
        logo_url = urljoin(sayfa_url, logo_url)
        # Örn: -300x127.png.webp -> .png formatına döndür (Airtable daha iyi okur)
        logo_url = re.sub(r'-\d+x\d+', '', logo_url).replace('.webp', '')

    # 4. Firmanın Kendi Web Sitesi
    web_url = ""
    for tr in soup.find_all('tr'):
        text = tr.get_text()
        if "Web Sitesi" in text or "Web Site" in text:
            a_tag = tr.find('a', href=True)
            if a_tag:
                web_url = a_tag['href']
                break

    if not web_url and not firma_adi:
        return None

    return {
        "firma_adi": firma_adi,
        "web_url": web_url,
        "logo": logo_url,
        "platform": platform_adi,
        "kaynak_link": sayfa_url
    }

def baslat():
    log("🚀 TARAMA BAŞLADI: İSDER & İMDER LOGO OPERASYONU")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    hedef_siteler = [
        {"url": "https://isder.org.tr/uyelerimiz/", "platform": "ISDER"},
        {"url": "https://imder.org.tr/uyelerimiz/", "platform": "IMDER"}
    ]

    for hedef in hedef_siteler:
        log(f"🔎 {hedef['platform']} listesi çekiliyor...")
        try:
            r = session.get(hedef["url"], timeout=30, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye detay sayfalarının linklerini topla
            firma_linkleri = set()
            for a in soup.find_all('a', href=True):
                link = a['href']
                # Linkin içinde platform adı geçiyorsa ve çok kısa değilse (filtreleme)
                if hedef['platform'].lower() in link.lower() and len(link.split('/')) > 4:
                    # Gereksiz sayfaları ele (haber, iletişim vs.)
                    if not any(x in link.lower() for x in ['haber', 'bulten', 'iletisim', 'etik', 'kurul', 'komite']):
                        firma_linkleri.add(urljoin(hedef["url"], link))

            log(f"📦 {len(firma_linkleri)} potansiyel firma bulundu. Detaylar inceleniyor...")

            for sayfa in firma_linkleri:
                try:
                    detay_r = session.get(sayfa, timeout=20, verify=False)
                    sonuc = veri_ayikla(detay_r.text, sayfa, hedef['platform'])
                    
                    if sonuc and sonuc['web_url']:
                        durum = airtable_ekle(sonuc)
                        log(f"✅ Eklendi: {sonuc['firma_adi']} ({durum})")
                        time.sleep(1) # Airtable hız limitine takılmamak için
                except Exception as e:
                    log(f"⚠️ Sayfa hatası ({sayfa}): {e}")
                    continue

        except Exception as e:
            log(f"💥 Ana liste hatası: {e}")

if __name__ == "__main__":
    baslat()
