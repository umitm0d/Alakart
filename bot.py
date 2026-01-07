import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# Tarayıcıyı "Görünmez" modda ayarla
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_links():
    # Örnek kategori sayfası
    url = "https://www.canlidizi14.com/kategori/digi/kismetse-olur-askin-gucu-izle"
    driver.get(url)
    time.sleep(5)
    
    # Bölüm linklerini topla
    elems = driver.find_elements(By.XPATH, "//a[contains(@href, 'bolum-izle')]")
    links = list(set([e.get_attribute("href") for e in elems]))
    return links

def extract_video(url):
    driver.get(url)
    # Sayfanın ve JavaScript'in yüklenmesi için 10 saniye bekle
    time.sleep(10)
    
    html = driver.page_source
    # Twitter m3u8 linkini ara
    match = re.search(r'https?://video\.twimg\.com/amplify_video/[^"\']+\.m3u8[^"\']*', html)
    if match:
        return match.group(0).replace("\\/", "/")
    return None

def main():
    print("Bot başlatıldı...")
    target_links = get_links()
    print(f"{len(target_links)} bölüm bulundu.")
    
    with open("canlidizi_listesi.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for link in target_links[:10]: # Test için ilk 10 bölüm
            name = link.split('/')[-1]
            print(f"İşleniyor: {name}...", end=" ")
            video = extract_video(link)
            if video:
                f.write(f"#EXTINF:-1, {name}\n{video}\n")
                print("OK!")
            else:
                print("YOK")
            time.sleep(2)

    driver.quit()

if __name__ == "__main__":
    main()
