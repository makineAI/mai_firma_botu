def veri_ayikla(soup):
    unvan = soup.select_one('h1.elementor-heading-title')
    unvan_text = unvan.get_text(strip=True) if unvan else None
    if not unvan_text or any(x in unvan_text.lower() for x in ['üyelik', 'etik', 'komite']): return None

    logo_url, web_url = "", ""
    inner_box = soup.select_one('.e-con-inner')
    
    if inner_box:
        # LOGO GARANTİSİ:
        img = inner_box.select_one('.elementor-widget-image img')
        if img:
            # 1. Strateji: srcset içindeki en yüksek çözünürlüklü (genellikle sonuncu) linki al
            srcset = img.get('srcset')
            if srcset:
                # Virgülle ayrılan linklerden en temiz olanı (genellikle ilk veya son) bulalım
                parts = srcset.split(',')
                # En geniş olanı (genellikle sonuncu) seçmek için:
                last_part = parts[-1].strip().split(' ')[0]
                logo_url = last_part
            
            # 2. Strateji: Eğer srcset yoksa veya başarısızsa src/data-src bak
            if not logo_url or "data:image" in logo_url:
                logo_url = img.get('src') or img.get('data-src')

        # WEB SİTESİ GARANTİSİ:
        for row in inner_box.find_all('tr'):
            if "Web Sitesi" in row.get_text():
                a = row.find('a')
                web_url = a.get('href') if a else row.find_all('td')[-1].get_text(strip=True)
                break

    if not web_url or "http" not in web_url: return None
    
    # URL Temizliği: .webp'den sonraki parametreleri temizle (Airtable'ın tanıması için)
    if logo_url and ".webp" in logo_url:
        logo_url = logo_url.split(".webp")[0] + ".webp"
    elif logo_url and ".png" in logo_url:
        logo_url = logo_url.split(".png")[0] + ".png"

    return {"firma_adi": unvan_text, "web_url": web_url, "logo": logo_url}
