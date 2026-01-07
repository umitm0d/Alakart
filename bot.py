import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_m3u8_from_network():
    try:
        logs = driver.get_log("performance")
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            if "Network.requestWillBeSent" in log["method"]:
                url = log["params"]["request"]["url"]
                # Twitter m3u8 linkini yakala
                if "video.twimg.com" in url and ".m3u8" in url:
                    return url
    except:
        pass
    return None

def main():
    base_url = "https://www.canlidizi14.com/kategori/digi/kismetse-olur-askin-gucu-izle"
    print(f"Ana sayfa açılıyor: {base_url}")
    driver.get(base_url)
    
    # Sayfanın yüklenmesi için bekle ve aşağı kaydır (Lazy load varsa tetikler)
    time.sleep(7)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(2)

    # 1. YÖNTEM: XPath ile 'bolum-izle' içeren tüm linkleri bul
    # 2. YÖNTEM: Regex ile tüm sayfa kaynağındaki linkleri ayıkla
    links = []
    page_source = driver.page_source
    raw_links = re.findall(r'href=["\'](https?://www\.canlidizi14\.com/[^"\']*?bolum-izle[^"\']*)["\']', page_source)
    
    for l in raw_links:
        if l not in links:
            links.append(l)

    if not links:
        print("Bölüm linki bulunamadı! Sayfa kaynağı kontrol ediliyor...")
        # Hata ayıklama için sayfa başlığını yazdıralım
        print(f"Sayfa Başlığı: {driver.title}")
        return

    print(f"Toplam {len(links)} bölüm bulundu. Tarama başlıyor...")

    with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        # GitHub sınırlamasına takılmamak için ilk 20 bölüm
        for link in links[:20]:
            print(f"İşleniyor: {link}")
            driver.get(link)
            
            # Twitter player'ın yüklenmesi için yeterli süre tanıyalım
            time.sleep(12) 
            
            video_url = get_m3u8_from_network()
            if video_url:
                name = link.split('/')[-1].replace(".html", "").replace("-", " ").title()
                f.write(f'#EXTINF:-1 group-title="Kismetse Olur", {name}\n{video_url}\n')
                print(f"BULDUM: {video_url[:50]}...")
            else:
                print("Video linki yakalanamadı.")
            
            time.sleep(1)

    driver.quit()

if __name__ == "__main__":
    main()
