# update_streams_invidious.py
#!/usr/bin/env python3
"""
YouTube Stream Updater - Invidious Version
Fetches YouTube stream URLs from Invidious and updates m3u8 playlists
"""

import json
import os
import sys
import argparse
import time
import re
import requests
from pathlib import Path
from urllib.parse import urlencode, urlparse

# Configuration
ENDPOINT = os.environ.get('ENDPOINT', 'https://yewtu.be')
FOLDER_NAME = os.environ.get('FOLDER_NAME', 'streams')
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Invidious instances as fallback
INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
    "https://inv.riverside.rocks",
    "https://invidious.snopyta.org",
    "https://yt.artemislena.eu"
]

# Create session
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=0
)
session.mount('http://', adapter)
session.mount('https://', adapter)

print("✓ Using Invidious instances for YouTube streams")

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
            delay = RETRY_DELAY * (2 ** (attempt - 2))
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

def get_live_stream_id_from_channel(channel_handle):
    """Get live stream ID from channel handle using Invidious"""
    for instance in INVIDIOUS_INSTANCES:
        try:
            print(f"  → Checking {instance} for channel: {channel_handle}")
            
            # Method 1: Try channel page
            channel_url = f"{instance}/channel/@{channel_handle}"
            response = session.get(channel_url, timeout=TIMEOUT)
            
            if response.status_code == 200:
                # Look for live stream in HTML
                live_pattern = r'"/watch\?v=([a-zA-Z0-9_-]{11})[^"]*"[^>]*>Live'
                matches = re.findall(live_pattern, response.text)
                
                if matches:
                    live_id = matches[0]
                    print(f"  ✓ Found live stream: {live_id}")
                    return live_id
                
                # Alternative pattern
                alt_pattern = r'data-video-id="([a-zA-Z0-9_-]{11})".*?LIVE'
                alt_matches = re.findall(alt_pattern, response.text, re.DOTALL)
                
                if alt_matches:
                    live_id = alt_matches[0]
                    print(f"  ✓ Found live stream (alt): {live_id}")
                    return live_id
            
            # Method 2: Try API
            api_url = f"{instance}/api/v1/channels/@{channel_handle}"
            api_response = session.get(api_url, timeout=TIMEOUT)
            
            if api_response.status_code == 200:
                data = api_response.json()
                if 'latestVideos' in data:
                    for video in data['latestVideos']:
                        if video.get('liveNow') or 'LIVE' in video.get('title', ''):
                            print(f"  ✓ Found live via API: {video['videoId']}")
                            return video['videoId']
            
        except Exception as e:
            print(f"  ✗ Failed with {instance}: {e}")
            continue
    
    print(f"  ✗ No live stream found for channel: {channel_handle}")
    return None

def fetch_stream_url(stream_config):
    """Fetch YouTube stream URL using Invidious API"""
    stream_type = stream_config.get('type', 'channel')
    stream_id = stream_config['id']
    slug = stream_config['slug']
    
    print(f"  Processing: {slug} ({stream_type}: {stream_id})")
    
    # For channels, first find the live stream ID
    if stream_type == 'channel':
        live_video_id = get_live_stream_id_from_channel(stream_id)
        if not live_video_id:
            return None, 'NoLiveStream'
        stream_id = live_video_id
        stream_type = 'video'
    
    # Now fetch the stream URL for the video
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{stream_id}"
            print(f"  → Fetching from: {api_url}")
            
            response = session.get(api_url, timeout=TIMEOUT)
            print(f"  → Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Get available formats
                format_streams = data.get('formatStreams', [])
                adaptive_formats = data.get('adaptiveFormats', [])
                
                if format_streams:
                    # Prefer formatStreams (combined video+audio)
                    best_stream = max(format_streams, key=lambda x: x.get('quality', ''))
                    stream_url = best_stream['url']
                    print(f"  ✓ Got stream URL (formatStreams)")
                    return generate_m3u8_content(stream_url, slug), None
                
                elif adaptive_formats:
                    # Use adaptive formats (need to combine video+audio)
                    video_streams = [f for f in adaptive_formats if f.get('type', '').startswith('video')]
                    if video_streams:
                        best_video = max(video_streams, key=lambda x: x.get('fps', 0))
                        stream_url = best_video['url']
                        print(f"  ✓ Got stream URL (adaptive)")
                        return generate_m3u8_content(stream_url, slug), None
                
                print(f"  ✗ No stream formats found")
                return None, 'NoStreamFormats'
                
            else:
                print(f"  ✗ API error: {response.status_code}")
                continue
                
        except Exception as e:
            print(f"  ✗ Failed with {instance}: {e}")
            continue
    
    return None, 'AllInstancesFailed'

def generate_m3u8_content(stream_url, slug):
    """Generate simple m3u8 content from direct stream URL"""
    # For Invidious, we get direct stream URLs, not m3u8
    # So we create a simple m3u8 that points to the stream
    m3u8_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2000000,RESOLUTION=1280x720
{stream_url}
"""
    return m3u8_content

def reverse_hls_quality(m3u8_content):
    """Reverse quality order - kept from original"""
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
    """Get output file path"""
    slug = stream_config['slug']
    subfolder = stream_config.get('subfolder', '')
    
    if subfolder:
        output_dir = Path(FOLDER_NAME) / subfolder
    else:
        output_dir = Path(FOLDER_NAME)
    
    return output_dir / f"{slug}.m3u8"

def delete_old_file(stream_config):
    """Delete old m3u8 file"""
    output_file = get_output_path(stream_config)
    
    try:
        if output_file.exists():
            output_file.unlink()
            print(f"  ⚠ Deleted old file: {output_file}")
            return True
    except Exception as e:
        print(f"  ⚠ Could not delete old file {output_file}: {e}")
        return False
    
    return False

def save_stream(stream_config, m3u8_content):
    """Save m3u8 content to file"""
    slug = stream_config['slug']
    output_file = get_output_path(stream_config)
    output_dir = output_file.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Reverse quality order if multiple streams
    reversed_content = reverse_hls_quality(m3u8_content)
    
    try:
        with open(output_file, 'w') as f:
            f.write(reversed_content)
        print(f"✓ Saved: {output_file}")
        return True
    except Exception as e:
        print(f"✗ Error saving {output_file}: {e}")
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Update YouTube stream m3u8 playlists using Invidious',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_streams_invidious.py config.json
  python update_streams_invidious.py config.json --endpoint https://yewtu.be
        """
    )
    
    parser.add_argument(
        'config_files',
        nargs='+',
        help='Configuration file(s) to process'
    )
    
    parser.add_argument(
        '--endpoint',
        default=ENDPOINT,
        help=f'Invidious instance URL (default: {ENDPOINT})'
    )
    
    parser.add_argument(
        '--folder',
        default=FOLDER_NAME,
        help=f'Output folder name (default: {FOLDER_NAME})'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=TIMEOUT,
        help=f'Request timeout in seconds (default: {TIMEOUT})'
    )
    
    parser.add_argument(
        '--retries',
        type=int,
        default=MAX_RETRIES,
        help=f'Maximum retry attempts (default: {MAX_RETRIES})'
    )
    
    return parser.parse_args()

def main():
    """Main execution function"""
    args = parse_arguments()
    
    global ENDPOINT, FOLDER_NAME, TIMEOUT, MAX_RETRIES
    ENDPOINT = args.endpoint
    FOLDER_NAME = args.folder
    TIMEOUT = args.timeout
    MAX_RETRIES = args.retries
    
    print("=" * 50)
    print("YouTube Stream Updater - Invidious Version")
    print("=" * 50)
    print(f"Primary instance: {ENDPOINT}")
    print(f"Fallback instances: {', '.join(INVIDIOUS_INSTANCES[1:])}")
    print(f"Output folder: {FOLDER_NAME}")
    print(f"Config files: {', '.join(args.config_files)}")
    print("=" * 50)
    
    total_success = 0
    total_fail = 0
    error_summary = {}
    
    for config_file in args.config_files:
        print(f"\n📄 Processing config: {config_file}")
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

if __name__ == "__main__":
    main()
