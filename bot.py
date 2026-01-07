import time
import json
import undetected_chromedriver as uc

def main():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Gerçek bir insan tarayıcısı gibi görünmek için:
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = uc.Chrome(options=options)
    
    # LİSTEYİ BURADAN GÜNCELLEYEBİLİRSİN
    links = [
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-58-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-57-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-56-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-55-bolum-izle.html"
    ]

    print(f"Toplam {len(links)} link isleniyor...")

    try:
        with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            for url in links:
                print(f"Aciliyor: {url.split('/')[-1]}...", end=" ", flush=True)
                driver.get(url)
                
                # Cloudflare ve videoların yüklenmesi için bekleme süresi
                time.sleep(15) 
                
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
                    name = url.split('/')[-1].replace(".html", "").replace("-", " ").upper()
                    f.write(f"#EXTINF:-1, {name}\n{video_url}\n")
                    print("BULDUM!")
                else:
                    print("BULAMADIM (Cloudflare Engeli veya Video Yok)")
                    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
