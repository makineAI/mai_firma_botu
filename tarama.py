import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time

# Airtable Bilgileri (GitHub Secrets'tan gelecek)
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

processed_urls = set() # Mükerrer kayıtları engellemek için

def airtable_gonder(veri):
    """Verileri tam olarak belirttiğin sütun isimleriyle Airtable'a gönderir."""
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
        
        # 1. Logo Bulma
        img = soup.find('img', {'src': lambda x: x and 'logo' in x.lower()})
        if img:
            logo = urljoin(web_url, img.get('src'))
        
        # 2. Hakkımızda Yazısını Bulma
        for a in soup.find_all('a', href=True):
            if any(k in a.text.lower() or k in a['href'].lower() for k in ['hakkimizda', 'kurumsal', 'about', 'hakkinda']):
                h_url = urljoin(web_url, a['href'])
                hr = requests.get(h_url, timeout=10, headers=headers)
                h_soup = BeautifulSoup(hr.text, 'html.parser')
                # Sayfadaki anlamlı paragrafları birleştir
                metin = " ".join([p.text.strip() for p in h_soup.find_all('p') if len(p.text.strip()) > 50])
                if metin:
                    hakkimizda = metin[:1200] + "..."
                break
    except:
        pass
    return logo, hakkimizda

def dernek_tara(ana_url):
    """İSDER ve İMDER sayfalarındaki üyeleri bulur."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"\n🚀 {ana_url} taranıyor...")
    
    try:
        r = requests.get(ana_url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Üye detay sayfalarının linklerini topla
        linkler = [urljoin(ana_url, a['href']) for a in soup.find_all('a', href=True) if '/uye/' in a['href']]
        
        for link in list(set(linkler)):
            try:
                detay_r = requests.get(link, headers=headers)
                detay_soup = BeautifulSoup(detay_r.text, 'html.parser')
                
                # Firma Ünvanı (h1 başlığından)
                unvan = detay_soup.find('h1').text.strip() if detay_soup.find('h1') else "Bilinmeyen Üye"
                
                # Firmanın asıl web sitesini bul (isder/imder dışındaki ilk link)
                web_tag = detay_soup.find('a', href=lambda x: x and 'http' in x and 'isder' not in x and 'imder' not in x)
                if not web_tag:
                    continue
                
                f_web_url = web_tag['href'].strip('/')
                
                # Mükerrer Kontrolü
                if f_web_url in processed_urls:
                    print(f"⏩ Mükerrer Atlandı: {unvan}")
                    continue
                
                print(f"🔎 Analiz Ediliyor: {unvan}")
                logo_link, hakkimizda_metni = icerik_ayikla(f_web_url)
                
                # Senin belirttiğin SÜTUN İSİMLERİ ile veriyi hazırlıyoruz
                veri = {
                    "firma_adi": unvan,
                    "web_url": f_web_url,
                    "logo": logo_link,
                    "hakkimizda": hakkimizda_metni
                }
                
                airtable_gonder(veri)
                processed_urls.add(f_web_url)
                time.sleep(2) # Siteyi yormamak için kısa bir ara
                
            except Exception as e:
                print(f"⚠️ Hata (Üye detayı): {e}")
                continue
    except Exception as e:
        print(f"❌ Ana sayfa tarama hatası: {e}")

if __name__ == "__main__":
    hedefler = [
        "https://isder.org.tr/uyelerimiz/",
        "https://imder.org.tr/uyelerimiz/"
    ]
    for hedef in hedefler:
        dernek_tara(hedef)
    print("\n✅ İşlem tamamlandı. Airtable'ı kontrol edebilirsin!")
