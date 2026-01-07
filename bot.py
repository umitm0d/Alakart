import time
import json
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def main():
    # Chrome ayarlarını hazırla
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    
    print("Cloudflare koruması aşılıyor...")
    driver = uc.Chrome(options=options)
    
    try:
        base_url = "https://www.canlidizi14.com/kategori/digi/kismetse-olur-askin-gucu-izle"
        driver.get(base_url)
        
        # Cloudflare'in çözülmesi için uzun süre bekle (15 saniye)
        time.sleep(15)
        
        print(f"Sayfa Başlığı: {driver.title}")
        
        # Linkleri ayıkla
        page_source = driver.page_source
        links = re.findall(r'href=["\'](https?://www\.canlidizi14\.com/[^"\']*?bolum-izle[^"\']*)["\']', page_source)
        links = sorted(list(set(links)), reverse=True)

        if not links:
            print("Hala link bulunamadı. Muhtemelen IP engellendi.")
            return

        print(f"{len(links)} bölüm bulundu. Videolar çekiliyor...")

        with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for link in links[:10]: # Test için 10 bölüm
                driver.get(link)
                time.sleep(12) # Video isteğinin atılması için bekle
                
                # Network loglarından m3u8 bul
                logs = driver.get_log("performance")
                video_url = None
                for entry in logs:
                    log = json.loads(entry["message"])["message"]
                    if "Network.requestWillBeSent" in log["method"]:
                        u = log["params"]["request"]["url"]
                        if "video.twimg.com" in u and ".m3u8" in u:
                            video_url = u
                            break
                
                if video_url:
                    name = link.split('/')[-1].replace(".html", "")
                    f.write(f"#EXTINF:-1, {name}\n{video_url}\n")
                    print(f"BAŞARILI: {name}")
                else:
                    print(f"BAŞARISIZ: {link.split('/')[-1]}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
