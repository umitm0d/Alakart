import os
import re
import requests
import sys

WORKER_URL = os.getenv("WORKER_URL")  # örn: https://macyayin.umittv.workers.dev
TEST_CHANNEL = "androstreamlivebs1.m3u8"

print("🔍 Worker testi başlatılıyor...")

try:
    playlist_url = f"{WORKER_URL}/checklist/{TEST_CHANNEL}"
    print(f"🌐 İstek atılıyor: {playlist_url}")
    r = requests.get(playlist_url, timeout=10)

    if r.status_code != 200:
        sys.exit(f"❌ HTTP hata kodu: {r.status_code}")

    content_type = r.headers.get("Content-Type", "")
    if "mpegurl" not in content_type:
        sys.exit(f"❌ Beklenmeyen Content-Type: {content_type}")

    m3u8_text = r.text
    print(f"📄 Playlist boyutu: {len(m3u8_text)} karakter")

    proxy_links = re.findall(r"/proxy/https%3A%2F%2F[^\s\n]+", m3u8_text)
    if not proxy_links:
        sys.exit("❌ Playlist içinde hiç proxy linki bulunamadı!")

    print(f"✅ {len(proxy_links)} proxy link bulundu. İlk örnek:")
    print("   ", proxy_links[0][:120] + "...")

    full_proxy_url = WORKER_URL + proxy_links[0]
    print(f"🔗 Proxy testi: {full_proxy_url}")
    pr = requests.get(full_proxy_url, stream=True, timeout=10)

    if pr.status_code != 200:
        sys.exit(f"❌ Proxy isteği başarısız! Kod: {pr.status_code}")

    first_chunk = next(pr.iter_content(chunk_size=512))
    if not first_chunk:
        sys.exit("❌ Proxy içerik boş döndü!")
    print(f"📦 İlk chunk boyutu: {len(first_chunk)} bayt")

    print("\n🎉 TÜM TESTLER GEÇTİ — Worker ve playlist düzgün çalışıyor!")

except requests.exceptions.RequestException as e:
    sys.exit(f"❌ Ağ hatası: {e}")
except Exception as e:
    sys.exit(f"❌ Beklenmeyen hata: {e}")
