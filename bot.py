import time
import json
import re
import undetected_chromedriver as uc

def main():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    
    # İZLEMEK İSTEDİĞİN BÖLÜMLERİ BURAYA YAPIŞTIR
    # Ana sayfayı taramadığımız için Cloudflare'e takılma ihtimali düşer
    links = [
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-58-bolum-izle.html",
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-57-bolum-izle.html,
        "https://www.canlidizi14.com/kismetse-olur-askin-gucu-56-bolum-izle.html"
    ]

    print("İşlem başlatılıyor...")
    driver = uc.Chrome(options=options)
    
    try:
        with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            for url in links:
                print(f"Bölüm açılıyor: {url.split('/')[-1]}")
                driver.get(url)
                time.sleep(15) # Sayfanın ve videonun yüklenmesi için zaman tanı
                
                # Network loglarından linki çek
                logs = driver.get_log("performance")
                found = False
                for entry in logs:
                    log = json.loads(entry["message"])["message"]
                    if "Network.requestWillBeSent" in log["method"]:
                        video_url = log["params"]["request"]["url"]
                        if "video.twimg.com" in video_url and ".m3u8" in video_url:
                            f.write(f"#EXTINF:-1, {url.split('/')[-1]}\n{video_url}\n")
                            print("BAŞARILI: Link yakalandı.")
                            found = True
                            break
                if not found:
                    print("BAŞARISIZ: Link bulunamadı.")
                    
    finally:
        driver.quit()
        print("Bitti. Dosyayı indirip kontrol et.")

if __name__ == "__main__":
    main()
