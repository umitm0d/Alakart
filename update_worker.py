import os
import re
import requests

# === ENV DEĞERLERİ ===
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
WORKER_NAME = "macyayin"
BASE_SCRIPT_PATH = "worker.js"

if not CF_ACCOUNT_ID or not CF_API_TOKEN:
    raise SystemExit("❌ Cloudflare bilgileri eksik! (Secrets kontrol et)")

print("🔍 Aktif domain aranıyor (birazcikspor25..99)...")

active_domain = None
for i in range(25, 100):
    url = f"https://birazcikspor{i}.xyz/"
    try:
        r = requests.head(url, timeout=5)
        if r.status_code == 200:
            active_domain = url
            break
    except:
        continue

if not active_domain:
    raise SystemExit("❌ Aktif domain bulunamadı.")

print(f"✅ Aktif domain bulundu: {active_domain}")

# Kanal ID ve Base URL
html = requests.get(active_domain, timeout=10).text
m = re.search(r'<iframe[^>]+id="matchPlayer"[^>]+src="event\.html\?id=([^"]+)"', html)
if not m:
    raise SystemExit("❌ Kanal ID bulunamadı.")
first_id = m.group(1)
print(f"📺 İlk kanal ID: {first_id}")

event_source = requests.get(active_domain + "event.html?id=" + first_id, timeout=10).text
b = re.search(r'var\s+baseurls\s*=\s*\[\s*"([^"]+)"', event_source)
if not b:
    raise SystemExit("❌ Base URL bulunamadı.")
base_url = b.group(1).rstrip("/")  # <-- Slash düzeltmesi burada!
print(f"🌐 Base URL bulundu: {base_url}")

# === Kanal listesi ===
channels = [
    ("beIN Sport 1 HD", "androstreamlivebs1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 2 HD", "androstreamlivebs2", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 3 HD", "androstreamlivebs3", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 4 HD", "androstreamlivebs4", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 5 HD", "androstreamlivebs5", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport Max 1 HD", "androstreamlivebsm1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport Max 2 HD", "androstreamlivebsm2", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("S Sport 1 HD", "androstreamlivess1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("S Sport 2 HD", "androstreamlivess2", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport HD", "androstreamlivets", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 1 HD", "androstreamlivets1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 2 HD", "androstreamlivets2", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 3 HD", "androstreamlivets3", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Tivibu Sport 4 HD", "androstreamlivets4", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Smart Sport 1 HD", "androstreamlivesm1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Smart Sport 2 HD", "androstreamlivesm2", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Euro Sport 1 HD", "androstreamlivees1", "https://i.hizliresim.com/pcrhcsx.jpg"),
    ("Euro Sport 2 HD", "androstreamlivees2", "https://i.hizliresim.com/pcrhcsx.jpg"),
]

# --- Toplu M3U ---
lines = ["#EXTM3U"]
for name, cid, logo in channels:
    lines.append(f'#EXTINF:-1 tvg-id="sport.tr" tvg-name="TR:{name}" tvg-logo="{logo}" group-title="DeaTHLesS",TR:{name}')
    full_url = f"{base_url}/{cid}.m3u8"
    lines.append(full_url)

with open("androiptv.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("✅ androiptv.m3u8 dosyası oluşturuldu.")

# --- Ayrı M3U dosyaları ---
out_dir = "channels"
os.makedirs(out_dir, exist_ok=True)

for name, cid, logo in channels:
    file_name = name.replace(" ", "_").replace("/", "_") + ".m3u8"
    full_url = f"{base_url}/{cid}.m3u8"
    content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f'#EXT-X-STREAM-INF:BANDWIDTH=5500000,AVERAGE-BANDWIDTH=8976000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25',
        full_url,
    ]
    with open(os.path.join(out_dir, file_name), "w", encoding="utf-8") as f:
        f.write("\n".join(content))

print(f"✅ {len(channels)} kanal '{out_dir}' klasörüne kaydedildi.")

# === Worker.js içindeki BASE_URL değiştir ===
with open(BASE_SCRIPT_PATH, "r", encoding="utf-8") as f:
    js_code = f.read()

new_js = re.sub(r'const BASE_URL\s*=\s*".*?"', f'const BASE_URL = "{base_url}/checklist/"', js_code)

# === Cloudflare'a yükle ===
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
