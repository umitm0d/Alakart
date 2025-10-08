import os
import re
import requests

# === ENV DEĞERLERİ ===
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
WORKER_NAME = "macyayin"  # Cloudflare'daki worker ismi
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
base_url = b.group(1)
print(f"🌐 Base URL bulundu: {base_url}")

# === Worker.js içindeki BASE_URL değiştir ===
with open(BASE_SCRIPT_PATH, "r", encoding="utf-8") as f:
    js_code = f.read()

new_js = re.sub(r'const BASE_URL\s*=\s*".*?"', f'const BASE_URL = "{base_url}"', js_code)

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
