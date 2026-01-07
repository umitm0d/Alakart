import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# Ağ trafiğini izlemek için gerekli ayar
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_m3u8_from_network():
    """Tarayıcının ağ trafiğini tarayarak m3u8 linkini bulur."""
    logs = driver.get_log("performance")
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        if "Network.requestWillBeSent" in log["method"]:
            url = log["params"]["request"]["url"]
            if "video.twimg.com" in url and ".m3u8" in url:
                return url
    return None

def main():
    # Önce kategori sayfasından bölüm linklerini alalım (veya manuel bir liste kullan)
    base_url = "https://www.canlidizi14.com/kategori/digi/kismetse-olur-askin-gucu-izle"
    driver.get(base_url)
    time.sleep(5)
    
    # Sayfadaki bölüm linklerini topla
    links = []
    elems = driver.find_elements("xpath", "//a[contains(@href, 'bolum-izle')]")
    for e in elems:
        href = e.get_attribute("href")
        if href not in links: links.append(href)

    print(f"{len(links)} bölüm bulundu. Tarama başlıyor...")

    with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for link in links[:15]: # GitHub süresi dolmasın diye ilk 15 bölüm
            print(f"İşleniyor: {link}")
            driver.get(link)
            
            # Videonun yüklenmesi ve isteğin atılması için bekle
            time.sleep(10) 
            
            video_url = get_m3u8_from_network()
            if video_url:
                name = link.split('/')[-1].replace(".html", "")
                f.write(f"#EXTINF:-1, {name}\n{video_url}\n")
                print(f"BULDUM: {video_url}")
            else:
                print("Bulunamadı.")

    driver.quit()

if __name__ == "__main__":
    main()
