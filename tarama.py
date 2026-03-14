import requests
import os
import sys

# Loglarin anlik gorunmesi icin zorlama
def log(mesaj):
    print(mesaj)
    sys.stdout.flush()

log("🚀 BOT BASLATILDI...")

# Airtable Bilgileri
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')

if not AIRTABLE_TOKEN:
    log("❌ HATA: AIRTABLE_TOKEN bulunamadi! GitHub Secrets'i kontrol et.")
    sys.exit(1)

def test_et(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }
    log(f"\n🔗 Deneniyor: {url}")
    try:
        # verify=False ekleyerek SSL takilmalarini geciyoruz, timeout'u kisa tutuyoruz
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        log(f"✅ Yanit Geldi! Durum Kodu: {r.status_code}")
        if r.status_code == 403:
            log("🚫 Site botu engelledi (403 Forbidden).")
        elif r.status_code == 200:
            log(f"✨ Siteye erisim saglandi. Sayfa uzunlugu: {len(r.text)}")
    except Exception as e:
        log(f"❌ Baglanti Hatasi: {str(e)}")

if __name__ == "__main__":
    log("🛠️ Baglanti testleri basliyor...")
    siteler = [
        "https://isder.org.tr/uyelerimiz/",
        "https://imder.org.tr/uyelerimiz/"
    ]
    for site in siteler:
        test_et(site)
    log("\n🏁 Test bitti.")
