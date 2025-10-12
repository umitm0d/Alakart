import os
import re
import requests

# === ENV DEĞERLERİ ===
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
PAGES_URL = os.getenv("PAGES_URL")  # örn: https://alakart.pages.dev
WORKER_NAME = "macyayin"
BASE_SCRIPT_PATH = "worker.js"

if not CF_ACCOUNT_ID or not CF_API_TOKEN or not PAGES_URL:
    raise SystemExit("❌ Eksik environment variable! (CF_ACCOUNT_ID, CF_API_TOKEN, PAGES_URL)")

base_url = PAGES_URL.rstrip('/') + '/checklist/'  # Slash ve /checklist ekle

# === Kanal listesi ===
channels = [
    ("beIN Sport 1 HD","androstreamlivebs1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 2 HD","androstreamlivebs2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 3 HD","androstreamlivebs3","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 4 HD","androstreamlivebs4","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 5 HD","androstreamlivebs5","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport Max 1 HD","androstreamlivebsm1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport Max 2 HD","androstreamlivebsm2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("S Sport 1 HD","androstreamlivess1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("S Sport 2 HD","androstreamlivess2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport HD","androstreamlivets","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 1 HD","androstreamlivets1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 2 HD","androstreamlivets2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 3 HD","androstreamlivets3","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 4 HD","androstreamlivets4","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Smart Sport 1 HD","androstreamlivesm1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Smart Sport 2 HD","androstreamlivesm2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Euro Sport 1 HD","androstreamlivees1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Euro Sport 2 HD","androstreamlivees2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii HD","androstreamlivetb","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 1 HD","androstreamlivetb1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 2 HD","androstreamlivetb2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 3 HD","androstreamlivetb3","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 4 HD","androstreamlivetb4","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 5 HD","androstreamlivetb5","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 6 HD","androstreamlivetb6","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 7 HD","androstreamlivetb7","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tabii 8 HD","androstreamlivetb8","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen HD","androstreamliveexn","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 1 HD","androstreamliveexn1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 2 HD","androstreamliveexn2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 3 HD","androstreamliveexn3","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 4 HD","androstreamliveexn4","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 5 HD","androstreamliveexn5","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 6 HD","androstreamliveexn6","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 7 HD","androstreamliveexn7","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Exxen 8 HD","androstreamliveexn8","https://i.hizliresim.com/pcrhcsx.jpg"),
]

# --- Toplu M3U ---
lines = ["#EXTM3U"]
os.makedirs("checklist", exist_ok=True)

for name, cid, logo in channels:
    lines.append(f'#EXTINF:-1 tvg-id="sport.tr" tvg-name="TR:{name}" tvg-logo="{logo}" group-title="DeaTHLesS",TR:{name}')
    full_url = f"{base_url}{cid}.m3u8"
    lines.append(full_url)

    # ayrı m3u8 dosyaları
    file_name = os.path.join("checklist", f"{cid}.m3u8")
    content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f'#EXT-X-STREAM-INF:BANDWIDTH=5500000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25',
        full_url
    ]
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

# toplu m3u8
with open("androiptv.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ {len(channels)} kanal M3U8 dosyaları 'checklist/' dizinine yazıldı.")
print("✅ Toplu androiptv.m3u8 dosyası oluşturuldu.")

# --- Worker.js içindeki BASE_URL değiştir ---
with open(BASE_SCRIPT_PATH, "r", encoding="utf-8") as f:
    js_code = f.read()

new_js = re.sub(r'const BASE_URL\s*=\s*".*?"', f'const BASE_URL = "{base_url}"', js_code)

# === Cloudflare Worker'a yükle ===
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/workers/scripts/{WORKER_NAME}"
headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/javascript",
}

print("🚀 Worker yükleniyor (Cloudflare)...")
r = requests.put(url, headers=headers, data=new_js.encode("utf-8"))

if r.status_code == 200 and r.json().get("success"):
    print("✅ Worker başarıyla yüklendi.")
else:
    print("❌ Worker yükleme hatası!", r.text)
