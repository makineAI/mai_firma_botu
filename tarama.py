import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time

# Airtable Bilgileri
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

def airtable_gonder(veri):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"fields": veri}, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            print(f"   ✅ Airtable'a başarıyla yazıldı: {veri['firma_adi']}")
        else:
            print(f"   ❌ Airtable Hatası: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Airtable Bağlantı Hatası: {e}")

def icerik_ayikla(web_url):
    print(f"   🌐 Firma sitesi taranıyor: {web_url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    logo, hakkimizda = "Bulunamadı", "Bilgi çekilemedi."
    try:
        r = requests.get(web_url, timeout=15, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        img = soup.find('img', {'src': lambda x: x and 'logo' in x.lower()})
        if img: logo = urljoin(web_url, img.get('src'))
        
        for a in soup.find_all('a', href=True):
            if any(k in a.text.lower() or k in a['href'].lower() for k in ['hakkimizda', 'kurumsal', 'about']):
                h_url = urljoin(web_url, a['href'])
                hr = requests.get(h_url, timeout=10, headers=headers)
                h_soup = BeautifulSoup(hr.text, 'html.parser')
                metin = " ".join([p.text.strip() for p in h_soup.find_all('p') if len(p.text.strip()) > 40])
                hakkimizda = metin[:1000] if metin else hakkimizda
                break
    except: pass
    return logo, hakkimizda

def tarama_yap(ana_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    print(f"\n🌍 Ana Siteye Giriş Yapılıyor: {ana_url}")
    
    try:
        # Timeout süresini artırdık ve doğrulamayı (verify) esnettik
        r = requests.get(ana_url, headers=headers, timeout=30)
        print(f"🔎 Sayfa yanıt verdi: {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        linkler = []
        # İSDER ve İMDER'deki firma linklerini daha geniş tarayalım
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Linkin içinde dernek adı geçiyorsa ve ana sayfa değilse al
            if any(domain in href for domain in ['isder.org.tr', 'imder.org.tr']):
                if not any(ek in href for ek in ['/category/', '/page/', '/tag/', 'tel:', 'mailto:']):
                    if len(href.split('/')) > 4: # Çok kısa linkleri (ana sayfa gibi) ele
                        linkler.append(href)
        
        linkler = list(set(linkler))
        print(f"📦 Bulunan potansiyel firma linki sayısı: {len(linkler)}")

        for link in linkler:
            print(f"\n📄 İncelenen sayfa: {link}")
            try:
                dr = requests.get(link, headers=headers, timeout=15)
                dsoup = BeautifulSoup(dr.text, 'html.parser')
                
                unvan = dsoup.find('h1').text.strip() if dsoup.find('h1') else None
                if not unvan:
                    print("   ⚠️ Firma unvanı bulunamadı, atlanıyor.")
                    continue

                print(f"   🏢 Firma: {unvan}")
                # Firmanın kendi web sitesini arıyoruz
                web_tag = dsoup.find('a', href=lambda x: x and 'http' in x and not any(h in x for h in ['isder.org', 'imder.org', 'facebook', 'twitter', 'instagram', 'linkedin']))
                
                if web_tag:
                    f_url = web_tag['href'].strip('/')
                    logo, hakkinda = icerik_ayikla(f_url)
                    
                    airtable_gonder({
                        "firma_adi": unvan,
                        "web_url": f_url,
                        "logo": logo,
                        "hakkimizda": hakkinda
                    })
                    time.sleep(2)
                else:
                    print("   ⚠️ Firma web sitesi linki bu sayfada bulunamadı.")
            except Exception as e:
                print(f"   ⚠️ Hata oluştu: {e}")
                continue
    except Exception as e:
        print(f"❌ Ana sayfaya ulaşılamadı: {e}")

if __name__ == "__main__":
    print("🚀 BOT BAŞLATILDI...")
    hedefler = [
        "https://isder.org.tr/uyelerimiz/",
        "https://imder.org.tr/uyelerimiz/"
    ]
    for h in hedefler:
        tarama_yap(h)
    print("\n🏁 TÜM İŞLEMLER BİTTİ.")
