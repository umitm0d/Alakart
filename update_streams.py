#!/usr/bin/env python3
"""
YouTube Stream Updater - Invidious alternatifleri
"""

import json
import os
import sys
import requests
import argparse
from pathlib import Path
import time
import random

# Çalışan Invidious instance'ları
INVIDIOUS_INSTANCES = [
    "https://vid.puffyan.us",
    "https://inv.tux.pizza",
    "https://y.com.sb",
    "https://invidious.nerdvpn.de",
    "https://yt.artemislena.eu",
    "https://invidious.flokinet.to",
    "https://inv.odyssey346.dev"
]

# Configuration
FOLDER_NAME = os.environ.get('FOLDER_NAME', 'streams')
TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 2

# Session oluştur
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://yewtu.be/'
})

def load_config(config_path):
    """Config dosyasını yükle"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded {len(config)} stream(s) from config")
        return config
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        sys.exit(1)

def get_random_instance():
    """Rastgele bir Invidious instance seç"""
    return random.choice(INVIDIOUS_INSTANCES)

def fetch_stream_from_invidious(stream_config):
    """Invidious API'den stream bilgisi al"""
    stream_type = stream_config.get('type', 'channel')
    stream_id = stream_config['id']
    slug = stream_config['slug']
    
    instance = get_random_instance()
    
    try:
        if stream_type == 'channel':
            # Kanalın canlı yayınını bul
            channel_url = f"{instance}/api/v1/channels/{stream_id}"
            print(f"🎬 {slug} - Checking channel...")
            
            response = session.get(channel_url, timeout=TIMEOUT)
            if response.status_code == 200:
                channel_data = response.json()
                
                # Son videoları kontrol et
                videos_url = f"{instance}/api/v1/channels/{stream_id}/videos"
                videos_response = session.get(videos_url, timeout=TIMEOUT)
                
                if videos_response.status_code == 200:
                    videos_data = videos_response.json()
                    
                    # Canlı yayınları bul
                    for video in videos_data.get('videos', []):
                        if video.get('liveNow') or video.get('lengthSeconds') == 0:
                            video_id = video['videoId']
                            print(f"  ✓ Live stream found: {video_id}")
                            return get_stream_url_from_video(instance, video_id, slug)
                    
                    print(f"  ⚠ No live stream found")
                    return None
                else:
                    print(f"  ✗ Failed to get videos: {videos_response.status_code}")
                    return None
            else:
                print(f"  ✗ Failed to get channel: {response.status_code}")
                return None
                
        elif stream_type == 'video':
            # Direkt video
            return get_stream_url_from_video(instance, stream_id, slug)
        else:
            print(f"✗ Unknown type: {stream_type}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error with {instance}: {e}")
        return None

def get_stream_url_from_video(instance, video_id, slug):
    """Video'dan stream URL'sini al"""
    try:
        # Video bilgilerini al
        video_url = f"{instance}/api/v1/videos/{video_id}"
        response = session.get(video_url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            video_data = response.json()
            
            # Format stream'lerini kontrol et
            format_streams = video_data.get('formatStreams', [])
            adaptive_formats = video_data.get('adaptiveFormats', [])
            
            # Tüm formatları birleştir
            all_formats = format_streams + adaptive_formats
            
            # m3u8 URL'lerini bul
            m3u8_urls = []
            for fmt in all_formats:
                url = fmt.get('url', '')
                if url and '.m3u8' in url:
                    m3u8_urls.append(url)
            
            if m3u8_urls:
                # İlk m3u8 URL'sini kullan
                m3u8_url = m3u8_urls[0]
                print(f"  ✓ Found m3u8 URL")
                
                # M3U8 içeriğini indir
                m3u8_response = session.get(m3u8_url, timeout=TIMEOUT)
                if m3u8_response.status_code == 200 and '#EXTM3U' in m3u8_response.text:
                    print(f"  ✓ Valid m3u8 content")
                    return m3u8_response.text
                else:
                    print(f"  ✗ Invalid m3u8 content")
                    return None
            else:
                print(f"  ✗ No m3u8 URLs found")
                return None
        else:
            print(f"  ✗ Failed to get video: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error getting video stream: {e}")
        return None

def fetch_stream_with_retry(stream_config):
    """Retry mekanizması ile stream al"""
    slug = stream_config['slug']
    
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            delay = RETRY_DELAY * (2 ** (attempt - 2))
            print(f"  → Retry {attempt}/{MAX_RETRIES} after {delay}s...")
            time.sleep(delay)
        
        result = fetch_stream_from_invidious(stream_config)
        if result is not None:
            return result
        
        if attempt < MAX_RETRIES:
            print(f"  → Attempt {attempt} failed, will retry...")
    
    print(f"  ✗ All {MAX_RETRIES} attempts failed for {slug}")
    return None

def reverse_hls_quality(m3u8_content):
    """Kalite sıralamasını ters çevir"""
    if not m3u8_content:
        return ""
        
    lines = m3u8_content.split('\n')
    stream_blocks = []
    current_block = []
    
    for line in lines:
        if line.startswith('#EXTM3U'):
            continue
        elif line.startswith('#EXT-X-STREAM-INF'):
            if current_block:
                stream_blocks.append(current_block)
            current_block = [line]
        elif current_block:
            current_block.append(line)
            if line and not line.startswith('#'):
                stream_blocks.append(current_block)
                current_block = []
    
    if current_block:
        stream_blocks.append(current_block)
    
    stream_blocks.reverse()
    result = ['#EXTM3U']
    for block in stream_blocks:
        result.extend(block)
    
    return '\n'.join(result)

def get_output_path(stream_config):
    """Çıktı dosya yolunu al"""
    slug = stream_config['slug']
    subfolder = stream_config.get('subfolder', '')
    
    if subfolder:
        output_dir = Path(FOLDER_NAME) / subfolder
    else:
        output_dir = Path(FOLDER_NAME)
    
    return output_dir / f"{slug}.m3u8"

def delete_old_file(stream_config):
    """Eski dosyayı sil"""
    output_file = get_output_path(stream_config)
    
    try:
        if output_file.exists():
            output_file.unlink()
            print(f"  ⚠ Deleted old file")
            return True
    except Exception as e:
        print(f"  ⚠ Could not delete old file: {e}")
    
    return False

def save_stream(stream_config, m3u8_content):
    """M3U8'i dosyaya kaydet"""
    if not m3u8_content:
        return False
        
    slug = stream_config['slug']
    output_file = get_output_path(stream_config)
    output_dir = output_file.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        reversed_content = reverse_hls_quality(m3u8_content)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(reversed_content)
        print(f"  ✓ Saved: {output_file}")
        return True
    except Exception as e:
        print(f"  ✗ Error saving: {e}")
        return False

def parse_arguments():
    """Komut satırı argümanlarını parse et"""
    parser = argparse.ArgumentParser(
        description='Update YouTube stream m3u8 playlists using Invidious'
    )
    
    parser.add_argument('config_files', nargs='+', help='Configuration file(s)')
    parser.add_argument('--folder', default=FOLDER_NAME, help='Output folder')
    parser.add_argument('--timeout', type=int, default=TIMEOUT, help='Request timeout')
    parser.add_argument('--retries', type=int, default=MAX_RETRIES, help='Max retries')
    
    return parser.parse_args()

def main():
    """Ana fonksiyon"""
    args = parse_arguments()
    
    global FOLDER_NAME, TIMEOUT, MAX_RETRIES
    FOLDER_NAME = args.folder
    TIMEOUT = args.timeout
    MAX_RETRIES = args.retries
    
    print("=" * 50)
    print("YouTube Stream Updater - Invidious")
    print("=" * 50)
    print(f"Output folder: {FOLDER_NAME}")
    print(f"Config files: {', '.join(args.config_files)}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Available instances: {len(INVIDIOUS_INSTANCES)}")
    print("=" * 50)
    
    total_success = 0
    total_fail = 0
    
    for config_file in args.config_files:
        print(f"\n📄 Processing: {config_file}")
        print("-" * 50)
        
        streams = load_config(config_file)
        
        for i, stream in enumerate(streams, 1):
            slug = stream.get('slug', 'unknown')
            print(f"\n[{i}/{len(streams)}] {slug}")
            
            m3u8_content = fetch_stream_with_retry(stream)
            
            if m3u8_content:
                if save_stream(stream, m3u8_content):
                    total_success += 1
                else:
                    total_fail += 1
                    delete_old_file(stream)
            else:
                total_fail += 1
                delete_old_file(stream)
    
    print("\n" + "=" * 50)
    print(f"✅ Complete: {total_success} successful, {total_fail} failed")
    print("=" * 50)

if __name__ == "__main__":
    main()
