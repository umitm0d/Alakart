import time
import json
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def main():
    # 1. PERFORMANS LOGLARINI AKTİF ET (Hatanın çözümü burası)
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Loglama yetkisini tanımlıyoruz
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    print("Tarayıcı başlatılıyor...")
    driver = uc.Chrome(options=options)
    
    links = [
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-58-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-57-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-56-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-55-bolum-izle.html"
    ]

    print(f"Toplam {len(links)} link işleniyor...")

    try:
        with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            for url in links:
                slug = url.split('/')[-1]
                print(f"Açılıyor: {slug}...", end=" ", flush=True)
                
                try:
                    driver.get(url)
                    time.sleep(15) # Video ve JS yüklenmesi için kritik bekleme
                    
                    video_url = None

                    # Yöntem A: Network Loglarını Tara
                    try:
                        logs = driver.get_log("performance")
                        for entry in logs:
                            log = json.loads(entry["message"])["message"]
                            if "Network.requestWillBeSent" in log["method"]:
                                u = log["params"]["request"]["url"]
                                if "video.twimg.com" in u and ".m3u8" in u:
                                    video_url = u
                                    break
                    except Exception as log_err:
                        print(f"(Log okuma hatası: {log_err})", end=" ")

                    # Yöntem B: Loglarda yoksa Sayfa Kaynağında Ara (Regex)
                    if not video_url:
                        source = driver.page_source
                        match = re.search(r'https?://video\.twimg\.com/[^"\']+\.m3u8[^"\']*', source)
                        if match:
                            video_url = match.group(0).replace("\\/", "/")

                    if video_url:
                        name = slug.replace(".html", "").replace("-", " ").upper()
                        f.write(f"#EXTINF:-1, {name}\n{video_url}\n")
                        f.flush()
                        print("BULDUM!")
                    else:
                        title = driver.title
                        print(f"BAŞARISIZ (Başlık: {title})")
                
                except Exception as e:
                    print(f"HATA: {e}")
                    
    finally:
        driver.quit()
        print("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
