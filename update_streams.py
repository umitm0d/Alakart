#!/usr/bin/env python3
"""
YouTube Stream Updater - yt-dlp versiyonu
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
import time

# Configuration
FOLDER_NAME = os.environ.get('FOLDER_NAME', 'streams')
TIMEOUT = 60
MAX_RETRIES = 2
RETRY_DELAY = 3

def load_config(config_path):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded {len(config)} stream(s) from config")
        return config
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        sys.exit(1)

def get_stream_with_ytdlp(stream_config):
    """yt-dlp ile doğrudan stream URL'si al"""
    stream_type = stream_config.get('type', 'channel')
    stream_id = stream_config['id']
    slug = stream_config['slug']
    
    try:
        if stream_type == 'channel':
            url = f"https://www.youtube.com/channel/{stream_id}/live"
        elif stream_type == 'video':
            url = f"https://www.youtube.com/watch?v={stream_id}"
        else:
            print(f"✗ Unknown type: {stream_type}")
            return None
        
        print(f"🎬 Fetching: {slug}")
        print(f"  → URL: {url}")
        
        # yt-dlp ile m3u8 URL'sini al
        cmd = [
            'yt-dlp',
            '-g',  # Sadece URL'yi al
            '--format', 'best',  # En iyi kalite
            '--no-warnings',
            '--quiet',
            '--no-check-certificates',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        
        if result.returncode == 0:
            m3u8_url = result.stdout.strip()
            if m3u8_url:
                print(f"  ✓ Stream found")
                
                # M3U8 içeriğini indir
                curl_cmd = [
                    'curl', '-s', '-L',
                    '--max-time', '30',
                    '--retry', '2',
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    m3u8_url
                ]
                
                curl_result = subprocess.run(curl_cmd, capture_output=True, text=True)
                
                if curl_result.returncode == 0 and '#EXTM3U' in curl_result.text:
                    print(f"  ✓ Valid m3u8 content received")
                    return curl_result.text
                else:
                    print(f"  ✗ Could not fetch m3u8 content")
                    return None
            else:
                print(f"  ✗ No stream URL returned")
                return None
        else:
            print(f"  ✗ yt-dlp error: {result.stderr.strip()}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout after {TIMEOUT}s")
        return None
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return None

def fetch_stream_with_retry(stream_config):
    """Stream alma işlemini retry ile yap"""
    slug = stream_config['slug']
    
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            delay = RETRY_DELAY * (2 ** (attempt - 2))
            print(f"  → Retry {attempt}/{MAX_RETRIES} after {delay}s...")
            time.sleep(delay)
        
        result = get_stream_with_ytdlp(stream_config)
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
    
    # Yüksek kalite önce
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
        description='Update YouTube stream m3u8 playlists using yt-dlp'
    )
    
    parser.add_argument('config_files', nargs='+', help='Configuration file(s)')
    parser.add_argument('--folder', default=FOLDER_NAME, help='Output folder')
    parser.add_argument('--timeout', type=int, default=TIMEOUT, help='Request timeout')
    parser.add_argument('--retries', type=int, default=MAX_RETRIES, help='Max retries')
    parser.add_argument('--retry-delay', type=int, default=RETRY_DELAY, help='Retry delay')
    
    return parser.parse_args()

def check_ytdlp():
    """yt-dlp'nin kurulu olduğunu kontrol et"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✓ yt-dlp version: {result.stdout.strip()}")
        return True
    except:
        print("✗ yt-dlp not found. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], 
                         check=True, capture_output=True)
            print("✓ yt-dlp installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install yt-dlp: {e}")
            return False

def main():
    """Ana fonksiyon"""
    args = parse_arguments()
    
    global FOLDER_NAME, TIMEOUT, MAX_RETRIES, RETRY_DELAY
    FOLDER_NAME = args.folder
    TIMEOUT = args.timeout
    MAX_RETRIES = args.retries
    RETRY_DELAY = args.retry_delay
    
    print("=" * 50)
    print("YouTube Stream Updater - yt-dlp")
    print("=" * 50)
    print(f"Output folder: {FOLDER_NAME}")
    print(f"Config files: {', '.join(args.config_files)}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Max retries: {MAX_RETRIES}")
    print("=" * 50)
    
    # yt-dlp kontrolü
    if not check_ytdlp():
        sys.exit(1)
    
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
    
    if total_success == 0:
        print("❌ No streams were updated")
        sys.exit(1)

if __name__ == "__main__":
    main()
