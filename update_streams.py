#!/usr/bin/env python3
"""
YouTube Stream Updater - yewtu.be endpoint versiyonu
"""

import json
import os
import sys
import argparse
import time
import re
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    import requests
    CLOUDSCRAPER_AVAILABLE = False
    print("⚠ Warning: cloudscraper not installed. Install with: pip install cloudscraper")
    print("⚠ Falling back to basic requests (JS challenges may not work)")
from pathlib import Path
from urllib.parse import urlencode, urlparse

# Configuration - yewtu.be endpoint
ENDPOINT = os.environ.get('ENDPOINT', 'https://yewtu.be')
FOLDER_NAME = os.environ.get('FOLDER_NAME', 'streams')
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Create a session for connection pooling
if CLOUDSCRAPER_AVAILABLE:
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
        delay=10
    )
    session = scraper
    print("✓ Using cloudscraper for JavaScript challenge bypass")
else:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=0
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    print("⚠ Using basic requests (limited challenge support)")


def load_config(config_path):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded {len(config)} stream(s) from config")
        return config
    except FileNotFoundError:
        print(f"✗ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in config file: {e}")
        sys.exit(1)


def fetch_stream_url_with_retry(stream_config):
    """Fetch stream URL with retry logic"""
    slug = stream_config['slug']
    last_error_type = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        if attempt > 1:
            delay = RETRY_DELAY * (2 ** (attempt - 2))  # Exponential backoff
            print(f"  → Retry {attempt}/{MAX_RETRIES} after {delay}s delay...")
            time.sleep(delay)
        
        result, error_type = fetch_stream_url(stream_config)
        if result is not None:
            return result, None
        
        last_error_type = error_type
        if attempt < MAX_RETRIES:
            print(f"  → Attempt {attempt} failed, will retry...")
    
    print(f"  ✗ All {MAX_RETRIES} attempts failed for {slug}")
    return None, last_error_type


def fetch_stream_url(stream_config):
    """Fetch the YouTube stream m3u8 URL from yewtu.be"""
    stream_type = stream_config.get('type', 'channel')
    stream_id = stream_config['id']
    slug = stream_config['slug']
    
    # yewtu.be için URL formatı
    if stream_type == 'video':
        # Video için direkt watch URL
        url = f"{ENDPOINT}/watch?v={stream_id}"
    elif stream_type == 'channel':
        # Kanal için live stream URL'si
        url = f"{ENDPOINT}/watch?v={stream_id}"
    else:
        print(f"✗ Unknown type '{stream_type}' for {slug}")
        return None
    
    print(f"  Fetching: {url}")
    
    try:
        # yewtu.be'den sayfayı çek
        response = session.get(
            url, 
            timeout=TIMEOUT, 
            allow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        print(f"  → Status Code: {response.status_code}")
        print(f"  → Content Length: {len(response.content)} bytes")
        
        response.raise_for_status()
        
        # yewtu.be sayfasından m3u8 URL'sini çıkart
        m3u8_url = extract_m3u8_from_yewtu(response.text, slug)
        
        if m3u8_url:
            print(f"  → Found m3u8 URL: {m3u8_url[:100]}...")
            
            # M3U8 içeriğini indir
            m3u8_response = session.get(
                m3u8_url,
                timeout=TIMEOUT,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Referer': url
                }
            )
            
            m3u8_response.raise_for_status()
            
            # M3U8 içeriğini kontrol et
            content_preview = m3u8_response.text[:200]
            if '#EXTM3U' in content_preview:
                print(f"  ✓ Valid m3u8 content received")
                return m3u8_response.text, None
            else:
                print(f"  ✗ Invalid m3u8 content")
                print(f"  → Preview: {content_preview[:100]}...")
                return None, 'InvalidM3U8'
        else:
            print(f"  ✗ Could not extract m3u8 URL from page")
            return None, 'NoM3U8URL'
        
    except Exception as e:
        error_type = type(e).__name__
        
        if 'timeout' in str(e).lower():
            error_type = 'Timeout'
            print(f"✗ Timeout error for {slug}: {e}")
        elif 'connection' in str(e).lower():
            error_type = 'ConnectionError'
            print(f"✗ Connection error for {slug}: {e}")
        elif hasattr(e, 'response') and e.response is not None:
            error_type = f'HTTPError-{e.response.status_code}'
            print(f"✗ HTTP error for {slug}: {e.response.status_code}")
        else:
            print(f"✗ Error for {slug}: {e}")
        
        return None, error_type


def extract_m3u8_from_yewtu(html_content, slug):
    """yewtu.be sayfasından m3u8 URL'sini çıkart"""
    # 1. Önce <video> tag'inde ara
    video_pattern = r'<video[^>]*src="([^"]*\.m3u8[^"]*)"'
    video_match = re.search(video_pattern, html_content, re.IGNORECASE)
    
    if video_match:
        m3u8_url = video_match.group(1)
        # URL tam değilse base URL ekle
        if m3u8_url.startswith('//'):
            m3u8_url = 'https:' + m3u8_url
        elif m3u8_url.startswith('/'):
            m3u8_url = 'https://yewtu.be' + m3u8_url
        return m3u8_url
    
    # 2. JSON verisi içinde ara
    json_pattern = r'{"url":"([^"]*\\.m3u8[^"]*)"'
    json_match = re.search(json_pattern, html_content)
    
    if json_match:
        m3u8_url = json_match.group(1).replace('\\/', '/')
        return m3u8_url
    
    # 3. Basit m3u8 pattern
    m3u8_pattern = r'https?://[^\s"\']*\.m3u8[^\s"\']*'
    m3u8_matches = re.findall(m3u8_pattern, html_content)
    
    if m3u8_matches:
        # İlk geçerli m3u8 URL'sini al
        for url in m3u8_matches:
            if 'googlevideo' in url:  # YouTube video URL'si
                return url
    
    # 4. Invidious API formatında ara
    api_pattern = r'https?://[^/]+/api/v1/videos/[^"\']+'
    api_match = re.search(api_pattern, html_content)
    
    if api_match:
        api_url = api_match.group(0)
        print(f"  → Found API URL: {api_url}")
        # API'den stream URL'sini al
        return get_stream_from_invidious_api(api_url)
    
    return None


def get_stream_from_invidious_api(api_url):
    """Invidious API'den stream URL'sini al"""
    try:
        response = session.get(api_url, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            # En yüksek kaliteli stream'i bul
            if 'formatStreams' in data and data['formatStreams']:
                # video/mp4 formatlarını filtrele, m3u8 ara
                for stream in data['formatStreams']:
                    if 'url' in stream and '.m3u8' in stream['url']:
                        return stream['url']
                
                # m3u8 bulunamazsa en yüksek kaliteli stream
                best_stream = max(data['formatStreams'], 
                                key=lambda x: x.get('quality', ''))
                return best_stream.get('url')
    except:
        pass
    
    return None


def reverse_hls_quality(m3u8_content):
    """Kalite sıralamasını ters çevir - yüksek kalite önce"""
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
    
    # Yüksek kalite önce gelecek şekilde ters çevir
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
    """Eski m3u8 dosyasını sil"""
    output_file = get_output_path(stream_config)
    
    try:
        if output_file.exists():
            output_file.unlink()
            print(f"  ⚠ Deleted old file: {output_file}")
            return True
    except Exception as e:
        print(f"  ⚠ Could not delete old file {output_file}: {e}")
    
    return False


def save_stream(stream_config, m3u8_content):
    """M3U8 içeriğini dosyaya kaydet"""
    slug = stream_config['slug']
    output_file = get_output_path(stream_config)
    output_dir = output_file.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        reversed_content = reverse_hls_quality(m3u8_content)
        with open(output_file, 'w') as f:
            f.write(reversed_content)
        print(f"✓ Saved: {output_file}")
        return True
    except Exception as e:
        print(f"✗ Error saving {output_file}: {e}")
        return False


def parse_arguments():
    """Komut satırı argümanlarını parse et"""
    parser = argparse.ArgumentParser(
        description='Update YouTube stream m3u8 playlists using yewtu.be',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_streams.py config.json
  python update_streams.py --endpoint https://yewtu.be config.json
  python update_streams.py config.json --retries 5 --timeout 60
        """
    )
    
    parser.add_argument('config_files', nargs='+', help='Configuration file(s)')
    parser.add_argument('--endpoint', default=ENDPOINT, help='yewtu.be endpoint URL')
    parser.add_argument('--folder', default=FOLDER_NAME, help='Output folder')
    parser.add_argument('--timeout', type=int, default=TIMEOUT, help='Request timeout')
    parser.add_argument('--retries', type=int, default=MAX_RETRIES, help='Max retries')
    parser.add_argument('--retry-delay', type=int, default=RETRY_DELAY, help='Retry delay')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--fail-on-error', action='store_true', help='Exit on error')
    
    return parser.parse_args()


def main():
    """Ana fonksiyon"""
    args = parse_arguments()
    
    global ENDPOINT, FOLDER_NAME, TIMEOUT, MAX_RETRIES, RETRY_DELAY
    ENDPOINT = args.endpoint
    FOLDER_NAME = args.folder
    TIMEOUT = args.timeout
    MAX_RETRIES = args.retries
    RETRY_DELAY = args.retry_delay
    
    print("=" * 50)
    print("YouTube Stream Updater - yewtu.be")
    print("=" * 50)
    print(f"Endpoint: {ENDPOINT}")
    print(f"Output folder: {FOLDER_NAME}")
    print(f"Config files: {', '.join(args.config_files)}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Max retries: {MAX_RETRIES}")
    print("=" * 50)
    
    total_success = 0
    total_fail = 0
    error_summary = {}
    
    for config_file in args.config_files:
        print(f"\n📄 Processing: {config_file}")
        print("-" * 50)
        
        streams = load_config(config_file)
        
        for i, stream in enumerate(streams, 1):
            slug = stream.get('slug', 'unknown')
            print(f"\n[{i}/{len(streams)}] Processing: {slug}")
            
            m3u8_content, error_type = fetch_stream_url_with_retry(stream)
            
            if m3u8_content:
                if save_stream(stream, m3u8_content):
                    total_success += 1
                else:
                    total_fail += 1
                    delete_old_file(stream)
                    error_summary['SaveError'] = error_summary.get('SaveError', 0) + 1
            else:
                total_fail += 1
                delete_old_file(stream)
                if error_type:
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1
    
    print("\n" + "=" * 50)
    print(f"Complete: {total_success} successful, {total_fail} failed")
    
    if error_summary:
        print("\nError Breakdown:")
        for error_type, count in sorted(error_summary.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {error_type}: {count}")
    
    print("=" * 50)
    
    if total_fail > 0 and args.fail_on_error:
        print(f"\n✗ Exiting with error code due to {total_fail} failures")
        sys.exit(1)


if __name__ == "__main__":
    main()
