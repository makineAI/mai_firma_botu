# 🤖 MakineAI Firma Tarama Botu

Bu bot, Excel dosyasındaki firmaların web sitelerini tarar, logolarını bulur ve sonuçları otomatik olarak Airtable'a aktarır.

## 🚀 Nasıl Çalışır?
1. `mai_firmalar.xlsx` dosyası güncellendiğinde otomatik tetiklenir.
2. Python ve BeautifulSoup kullanarak web sitelerini analiz eder.
3. Airtable API aracılığıyla verileri tabloya işler.

## 📁 Dosya Yapısı
- `tarama.py`: Ana işlem kodu.
- `requirements.txt`: Gerekli kütüphaneler.
- `.github/workflows/run_python.yml`: Otomasyon ayarları.
