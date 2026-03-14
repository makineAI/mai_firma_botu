import re # Dosya ismini temizlemek için en üste ekle

def veri_ayikla(soup):
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']): return None

    logo_url, web_url = "", ""
    inner_box = soup.select_one('.e-con-inner')
    
    if inner_box:
        # --- LOGO TEMİZLEME OPERASYONU ---
        img = inner_box.select_one('.elementor-widget-image img')
        if img:
            # Önce srcset'e bak, en büyük resmi (genellikle sonuncu) seç
            srcset = img.get('srcset')
            if srcset:
                parts = [p.strip().split(' ')[0] for p in srcset.split(',')]
                logo_url = parts[-1] # En büyük boyut
            else:
                logo_url = img.get('src') or img.get('data-src')

            # KRİTİK ADIM: Airtable için URL'yi "Saf" hale getir
            # Örnek: -300x300.png.webp -> .png.webp yapar
            if logo_url:
                logo_url = re.sub(r'-\d+x\d+', '', logo_url)

        # --- WEB URL ---
        for row in inner_box.find_all('tr'):
            if "Web Sitesi" in row.get_text():
                a = row.find('a')
                web_url = a.get('href') if a else row.find_all('td')[-1].get_text(strip=True)
                break

    if not web_url or "http" not in web_url: return None
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}
