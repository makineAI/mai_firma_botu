def veri_ayikla(soup):
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']): return None

    logo_url, web_url = "", ""
    inner_box = soup.select_one('.e-con-inner')
    
    if inner_box:
        # --- LOGO CERRAHİSİ ---
        img = inner_box.select_one('.elementor-widget-image img')
        if img:
            # 1. Strateji: srcset içindeki en yüksek çözünürlüklü (genellikle sonuncu) linki al
            srcset = img.get('srcset')
            if srcset:
                # Virgülle ayrılan linklerden en temizini (genellikle sonuncuyu) seç
                parts = [p.strip().split(' ')[0] for p in srcset.split(',')]
                if parts:
                    logo_url = parts[-1] # En büyük boyut genellikle sondadır
            
            # 2. Strateji: Eğer srcset yoksa src bak
            if not logo_url or "data:image" in logo_url:
                logo_url = img.get('src') or img.get('data-src')

        # --- WEB SİTESİ ---
        for row in inner_box.find_all('tr'):
            if "Web Sitesi" in row.get_text():
                a = row.find('a')
                web_url = a.get('href') if a else row.find_all('td')[-1].get_text(strip=True)
                break

    if not web_url or "http" not in web_url: return None
    
    # --- KRİTİK: URL TEMİZLİĞİ ---
    # Airtable, sonunda -300x300.webp gibi ekler olan linkleri bazen reddeder.
    # Orijinal dosyaya gitmek için varsa bu ekleri temizliyoruz.
    if logo_url:
        import re
        # Örnek: -300x300.png.webp -> .png veya .webp haline getirir
        logo_url = re.sub(r'-\d+x\d+', '', logo_url)
    
    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}
