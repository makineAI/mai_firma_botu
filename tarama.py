import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time

# Airtable Bilgileri
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

processed_urls = set()

def airtable_gonder(veri):
    if not all([AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME]):
        print("❌ Hata: GitHub Secrets eksik!")
        return
    
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json={"fields": veri}, headers=headers)
    if response.status_code in [200, 201]:
        print(f"✅ Airtable'a Eklendi: {veri.get('firma_adi')}")
    else:
        print(f"❌ Airtable Hatası: {response.text}")

def icerik_ayikla(web_url):
    """Firmanın kendi sitesine girer; logo ve hakkımızda yazısını çeker."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    logo, hakkimizda = "Bulunamadı", "Bilgi çekilemedi."
    try:
        r = requests.get(web_url, timeout=15, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        img = soup.find('img', {'src': lambda x: x and 'logo' in x.lower()})
        if img:
            logo = urljoin(web_url, img.get('src'))
        
        for a in soup.find_all('a', href=True):
            if any(k in a.text.lower() or k in a['href'].lower() for k in ['hakkimizda', 'kurumsal', 'about', 'hakkinda']):
                h_url = urljoin(web_url, a['href'])
                hr = requests.get(h_url, timeout=10, headers=headers)
                h_soup = BeautifulSoup(hr.text, 'html.parser')
                metin = " ".join([p.text.strip() for p in h_soup.find_all('p') if len(p.text.strip()) > 50])
                if metin:
                    hakkimizda = metin[:1200] + "..."
                break
    except:
        pass
    return logo, hakkimizda

def dernek_tara(ana_kategori_url):
    """Derneklerin tüm sayfalarını (Pagination) gezer."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1'den 15'e kadar tüm sayfaları (page/1, page/2) dolaş
    for sayfa in range(1, 15):
        url = f"{ana_kategori_url}page/{sayfa}/" if sayfa > 1 else ana_kategori_url
        print(f"\n🚀 Sayfa Taranıyor: {url}")
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                print("🏁 Sayfalar bitti veya ulaşılamadı.")
                break # Sayfa kalmadıysa döngüden çık
                
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Üye detay sayfalarının linklerini bul (WordPress standart başlık veya READ MORE linkleri)
            linkler = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.text.lower()
                # Ana domaine ait olup menü linki olmayanları ve "read more" olanları al
                if ('isder.org.tr' in href or 'imder.org.tr' in href) and '/category/' not in href and '/page/' not in href and '/iletisim' not in href:
                    if 'read more' in text or 'devam' in text or a.parent.name in ['h2', 'h3']:
                        linkler.append(href)
            
            linkler = list(set(linkler))
            if not linkler:
                continue

            for link in linkler:
                try:
                    detay_r = requests.get(link, headers=headers, timeout=10)
                    detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                    
                    # Firma Ünvanı (h1 başlığı)
                    unvan_tag = detay_soup.find('h1')
                    if not unvan_tag: continue
                    unvan = unvan_tag.text.strip()
                    
                    # Firmanın asıl web sitesini bul (Sosyal medya olmayan ilk dış link)
                    haric_tut = ['isder.org', 'imder.org', 'facebook', 'twitter', 'instagram', 'linkedin', 'youtube']
                    web_tag = detay_soup.find('a', href=lambda x: x and 'http' in x and not any(h in x for h in haric_tut))
                    
                    if not web_tag: continue
                    
                    f_web_url = web_tag['href'].strip('/')
                    
                    if f_web_url in processed_urls:
                        print(f"⏩ Mükerrer Atlandı: {unvan}")
                        continue
                    
                    print(f"🔎 Analiz Ediliyor: {unvan} ({f_web_url})")
                    logo_link, hakkimizda_metni = icerik_ayikla(f_web_url)
                    
                    veri = {
                        "firma_adi": unvan,
                        "web_url": f_web_url,
                        "logo": logo_link,
                        "hakkimizda": hakkimizda_metni
                    }
                    
                    airtable_gonder(veri)
                    processed_urls.add(f_web_url)
                    time.sleep(1) # Siteleri yormamak için bekleme
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"❌ Bağlantı hatası: {e}")
            break

if __name__ == "__main__":
    # Sitelerin gerçek liste (kategori) adresleri
    hedefler = [
        "https://isder.org.tr/category/uyelerimiz/",
        "https://imder.org.tr/category/uyelerimiz/"
    ]
    for hedef in hedefler:
        dernek_tara(hedef)
    print("\n✅ Tarama işlemi tamamen bitti!")
