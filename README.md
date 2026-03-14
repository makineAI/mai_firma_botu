# 🤖 MakineAI Web Tarama Botu

Bu bot, belirlenen firmaların resmi web sitelerine gider, site içeriğini analiz eder ve firmaya ait kurumsal bilgileri (logo, iletişim vb.) ayıklayarak Airtable'a aktarır.

## 🔍 Neler Yapar?
1. Verilen web adreslerini tek tek ziyaret eder.
2. Web sitesi kodları (HTML) içinde logo ve kurumsal kimlik izlerini sürer.
3. Bulduğu verileri anlık olarak Airtable veritabanına işler.

## 🛠️ Teknik Altyapı
- **Dil:** Python 3.9
- **Kütüphaneler:** BeautifulSoup4 (Web Kazıma), Requests (Web Bağlantısı)
- **Veri Deposu:** Airtable API
