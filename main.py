import os
import requests
import xml.etree.ElementTree as ET
import dropbox

# ----------------- Ayarlar -----------------
XML_URL = "https://belgeselsemo.com.tr/yayin-akisi2/xml/turkey3.xml"
LOCAL_XML = "epg.xml"
UPDATED_XML = "epg_updated.xml"
CHANNEL_ID_FILE = "kanalid.txt"
DROPBOX_PATH = "/epg_updated.xml"

# Dropbox OAuth bilgilerini GitHub Secrets (ortam değişkenleri) üzerinden al
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")

# Türkçe karakter düzeltme haritası
turkish_map = str.maketrans(
    "ÇŞĞÜİÖçşıüö",
    "csguiocsiuo"
)

# ----------------- Fonksiyonlar -----------------
def download_xml():
    print("🔎 XML indiriliyor...")
    r = requests.get(XML_URL, timeout=15)
    r.raise_for_status()
    with open(LOCAL_XML, "w", encoding="utf-8") as f:
        f.write(r.text)
    print(f"✅ {LOCAL_XML} indirildi.")

def update_channels():
    tree = ET.parse(LOCAL_XML)
    root = tree.getroot()

    with open(CHANNEL_ID_FILE, "w", encoding="utf-8") as f_txt:
        for channel in root.findall("channel"):
            display_name_elem = channel.find("display-name")
            if display_name_elem is not None:
                name = display_name_elem.text.strip()
                ch_id = name.lower().translate(turkish_map).replace(" ", "")
                ch_id = ch_id.replace("hd", "").replace(".tr", "")
                channel.set("id", ch_id)
                f_txt.write(f"{name} => {ch_id}\n")

    tree.write(UPDATED_XML, encoding="utf-8", xml_declaration=True)
    print(f"✅ {UPDATED_XML} ve {CHANNEL_ID_FILE} oluşturuldu.")

def get_dropbox_access_token():
    url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": DROPBOX_REFRESH_TOKEN,
        "client_id": DROPBOX_APP_KEY,
        "client_secret": DROPBOX_APP_SECRET
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

def upload_to_dropbox():
    access_token = get_dropbox_access_token()
    dbx = dropbox.Dropbox(access_token)
    with open(UPDATED_XML, "rb") as f:
        dbx.files_upload(f.read(), DROPBOX_PATH, mode=dropbox.files.WriteMode.overwrite)
    print(f"✅ {UPDATED_XML} Dropbox'a yüklendi: {DROPBOX_PATH}")

# ----------------- Ana Program -----------------
if __name__ == "__main__":
    download_xml()
    update_channels()
    upload_to_dropbox()
