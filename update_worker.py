import os
import re
import requests

# === ENV DEĞERLERİ ===
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
PAGES_URL = os.getenv("PAGES_URL")  # Cloudflare Pages URL
WORKER_NAME = "macyayin"
BASE_SCRIPT_PATH = "worker.js"

if not CF_ACCOUNT_ID or not CF_API_TOKEN or not PAGES_URL:
    raise SystemExit("❌ Eksik environment variable! (CF_ACCOUNT_ID, CF_API_TOKEN, PAGES_URL)")

base_url = PAGES_URL.rstrip('/')  # Slash kontrolü

# === Kanal listesi ===
channels = [
    ("beIN Sport 1 HD","androstreamlivebs1","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 2 HD","androstreamlivebs2","https://i.hizliresim.com/pcrhcsx.jpg"),
    ("beIN Sport 3 HD","androstreamlivebs3","https://i.hizliresim.com/pcrhcsx.jpg"),
]

# --- Toplu M3U ---
lines = ["#EXTM3U"]
for name, cid, logo in channels:
    lines.append(f'#EXTINF:-1 tvg-id="sport.tr" tvg-name="TR:{name}" tvg-logo="{logo}" group-title="DeaTHLesS",TR:{name}')
    lines.append(f"{base_url}/{cid}.m3u8")

with open("androiptv.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("✅ androiptv.m3u8 dosyası oluşturuldu.")

# --- Worker.js içindeki BASE_URL değiştir ---
with open(BASE_SCRIPT_PATH, "r", encoding="utf-8") as f:
    js_code = f.read()

new_js = re.sub(
    r'const BASE_URL\s*=\s*".*?"',
    f'const BASE_URL = "{base_url}/checklist/"',
    js_code
)

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
