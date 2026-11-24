import os
import sys
import re
import time
import shutil
import threading
import uuid
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import yt_dlp.utils
import imageio_ffmpeg

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def setup_ffmpeg():
    # 1. Check if standard system ffmpeg is installed and available
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 2. Check bundled imageio_ffmpeg
    try:
        raw_exe = imageio_ffmpeg.get_ffmpeg_exe()
        bin_dir = os.path.dirname(raw_exe)
        target_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        target_exe = os.path.join(bin_dir, target_name)
        
        if not os.path.exists(target_exe):
            try:
                shutil.copyfile(raw_exe, target_exe)
                if sys.platform != "win32":
                    os.chmod(target_exe, 0o755)
                print(f"Created standard ffmpeg executable at: {target_exe}")
            except Exception as e:
                print(f"Notice on copying ffmpeg: {e}")
                
        # Prepend binaries directory to PATH so yt-dlp's FFmpegFD finds ffmpeg
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            
        return target_exe if os.path.exists(target_exe) else raw_exe
    except Exception as e:
        print(f"Warning on locating ffmpeg: {e}")
        return "ffmpeg"

FFMPEG_PATH = setup_ffmpeg()

# Ensure user deno bin directory is in PATH if present
deno_dir = os.path.expanduser("~/.deno/bin")
if os.path.exists(deno_dir) and deno_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = deno_dir + os.pathsep + os.environ.get("PATH", "")

# Store active download tasks in memory
active_downloads = {}

def cleanup_old_downloads(max_age_seconds=3600):
    """Background worker to automatically clean up temporary files on a public web server."""
    while True:
        try:
            time.sleep(300)  # Check every 5 minutes
            now = time.time()
            for item in DOWNLOAD_DIR.glob("*"):
                if item.is_file():
                    # Skip incomplete downloads currently being written and gitkeep
                    if item.suffix in [".part", ".ytdl"] or item.name == ".gitkeep":
                        continue
                    file_age = now - item.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            item.unlink()
                            print(f"[Cleanup] Removed expired public download: {item.name}")
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Cleanup Notice] {e}")

# Start background cleanup thread for production websites
cleanup_worker = threading.Thread(target=cleanup_old_downloads, daemon=True)
cleanup_worker.start()

def clean_ansi(text):
    if not text:
        return ""
    return re.sub(r'(\x1b|\x1B|≡|\^\[)?\[[0-9;]*[a-zA-Z]?', '', str(text)).strip()

def parse_timestamp(ts):
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    if not s:
        return None
    parts = s.split(':')
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None

def format_speed(speed_bytes_sec):
    if not speed_bytes_sec:
        return ""
    try:
        s = float(speed_bytes_sec)
        if s >= 1024 * 1024:
            return f"{s / (1024 * 1024):.2f} MiB/s"
        elif s >= 1024:
            return f"{s / 1024:.1f} KiB/s"
        else:
            return f"{s:.0f} B/s"
    except Exception:
        return ""

def format_eta(seconds):
    if seconds is None:
        return ""
    try:
        s = int(seconds)
        mins, secs = divmod(s, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
    except Exception:
        return ""

def clean_video_url(url):
    if not url:
        return ""
    # Remove tracking query parameters from media links
    if "youtu.be" in url or "youtube.com" in url:
        url = re.sub(r'([?&])(si|feature)=[^&]+', '', url)
    elif "reddit.com" in url or "redd.it" in url:
        url = re.sub(r'[?&]utm_[^&]+', '', url)
        url = re.sub(r'[?&](context|ref|share_id)=[^&]+', '', url)
    if '?' in url and not url.split('?')[1]:
        url = url.rstrip('?')
    return url.strip()

# Cookie file configuration for datacenter IPs (DigitalOcean, AWS, Render, etc.)
COOKIES_FILE = BASE_DIR / "cookies.txt"

def sync_cookies_from_env():
    """Sync cookies from environment variable if present (ideal for cloud platforms like DigitalOcean)."""
    env_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
    if env_cookies:
        try:
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write(env_cookies)
            print(f"[Cookies] Successfully loaded YouTube cookies from YOUTUBE_COOKIES env var ({len(env_cookies)} chars).")
        except Exception as e:
            print(f"[Cookies] Failed to write cookies from env: {e}")

sync_cookies_from_env()

def get_base_ydl_opts():
    js_runtimes = {}
    if shutil.which("deno"):
        js_runtimes['deno'] = {}
    if shutil.which("node"):
        js_runtimes['node'] = {}
    if not js_runtimes:
        js_runtimes = {'deno': {}, 'node': {}}

    has_cookies = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 10

    # Choose best player client sequence based on whether authenticated cookies are available
    if has_cookies:
        youtube_clients = ['web', 'tv_samsung', 'android', 'web_embedded']
    else:
        youtube_clients = ['tv_samsung', 'visionos', 'web_embedded', 'android', 'ios']

    opts = {
        'ffmpeg_location': FFMPEG_PATH,
        'noplaylist': True,
        'windowsfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
        'js_runtimes': js_runtimes,
        'remote_components': ['ejs:github'],
        'extractor_args': {
            'youtube': {
                'player_client': youtube_clients,
            }
        },
    }

    if has_cookies:
        opts['cookiefile'] = str(COOKIES_FILE)

    return opts

def detect_platform_from_url(url, extractor_key=None):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return {"id": "youtube", "name": "YouTube", "color": "#ff0033", "icon": "youtube"}
    elif "tiktok.com" in u:
        return {"id": "tiktok", "name": "TikTok", "color": "#00f2fe", "icon": "tiktok"}
    elif "instagram.com" in u:
        return {"id": "instagram", "name": "Instagram", "color": "#e1306c", "icon": "instagram"}
    elif "twitter.com" in u or "x.com" in u:
        return {"id": "twitter", "name": "X / Twitter", "color": "#1da1f2", "icon": "twitter"}
    elif "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
        return {"id": "facebook", "name": "Facebook", "color": "#1877f2", "icon": "facebook"}
    elif "reddit.com" in u or "redd.it" in u:
        return {"id": "reddit", "name": "Reddit", "color": "#ff4500", "icon": "reddit"}
    elif "twitch.tv" in u:
        return {"id": "twitch", "name": "Twitch", "color": "#9146ff", "icon": "twitch"}
    elif "vimeo.com" in u:
        return {"id": "vimeo", "name": "Vimeo", "color": "#1ab7ea", "icon": "vimeo"}
    elif "pinterest.com" in u or "pin.it" in u:
        return {"id": "pinterest", "name": "Pinterest", "color": "#bd081c", "icon": "pinterest"}
    elif "soundcloud.com" in u:
        return {"id": "soundcloud", "name": "SoundCloud", "color": "#ff5500", "icon": "soundcloud"}
    elif extractor_key:
        return {"id": "generic", "name": extractor_key.capitalize(), "color": "#10b981", "icon": "video"}
    else:
        return {"id": "generic", "name": "Multi-Media", "color": "#10b981", "icon": "video"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/detect-platform", methods=["POST"])
def detect_platform():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    return jsonify({"success": True, "platform": detect_platform_from_url(url)})

@app.route("/api/info", methods=["POST"])
def get_video_info():
    data = request.get_json() or {}
    url = clean_video_url(data.get("url", "").strip())
    if not url:
        return jsonify({"success": False, "error": "Please provide a valid video URL"}), 400

    try:
        ydl_opts = get_base_ydl_opts()
        ydl_opts['extract_flat'] = False
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return jsonify({"success": False, "error": "Could not extract media information from this link"}), 400

            extractor_key = info.get("extractor_key") or info.get("extractor", "")
            platform = detect_platform_from_url(url, extractor_key)

            formats = info.get("formats", [])
            resolutions = set()
            has_audio = False
            for f in formats:
                h = f.get("height")
                if h and f.get("vcodec") != "none":
                    resolutions.add(h)
                if f.get("acodec") != "none":
                    has_audio = True

            sorted_res = sorted(list(resolutions), reverse=True)

            duration_sec = info.get("duration", 0)
            if duration_sec:
                mins, secs = divmod(int(duration_sec), 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"
            else:
                duration_str = "Video / Audio Clip"

            # Find direct stream or embed URL
            embed_url = ""
            video_id = info.get("id", "")
            if platform["id"] == "youtube" and video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"
            elif platform["id"] == "vimeo" and video_id:
                embed_url = f"https://player.vimeo.com/video/{video_id}"

            stream_url = ""
            for f in reversed(formats):
                if f.get("ext") == "mp4" and f.get("url") and f.get("vcodec") != "none":
                    stream_url = f.get("url")
                    if f.get("acodec") != "none":
                        break
            if not stream_url:
                stream_url = info.get("url", "")

            result = {
                "success": True,
                "platform": platform,
                "video_id": video_id,
                "embed_url": embed_url,
                "stream_url": stream_url,
                "title": info.get("title", "Media"),
                "uploader": info.get("uploader") or info.get("channel") or info.get("creator") or platform["name"],
                "duration": duration_str,
                "duration_raw": duration_sec,
                "thumbnail": info.get("thumbnail", ""),
                "view_count": f"{info.get('view_count', 0):,}" if info.get('view_count') else "N/A",
                "available_resolutions": sorted_res,
                "has_audio": has_audio
            }
            return jsonify(result)
    except Exception as e:
        err_msg = str(e)
        if "Sign in to confirm you're not a bot" in err_msg:
            err_msg = "YouTube bot verification triggered on cloud server IP. Add your cookies (via YOUTUBE_COOKIES environment variable or cookies.txt) to enable downloads."
        elif "/s/" in url and ("reddit.com" in url or "redd.it" in url):
            err_msg = "Reddit shortlinks (/s/) cannot be extracted because Reddit redirects them to the subreddit homepage. Please open the post in your browser and copy the full URL (e.g., reddit.com/r/.../comments/...)."
        elif "Account authentication is required" in err_msg and "reddit" in err_msg.lower():
            err_msg = "Reddit has blocked anonymous guest access. Please copy the direct post URL or provide authenticated cookies."
        return jsonify({"success": False, "error": err_msg}), 400

def run_download_task(download_id, url, quality, title, thumbnail, platform_name, start_time=None, end_time=None):
    start_sec = parse_timestamp(start_time)
    end_sec = parse_timestamp(end_time)
    is_clip = (start_sec is not None and end_sec is not None and end_sec > start_sec)

    clip_label = ""
    if is_clip:
        clip_label = f"{format_eta(start_sec)} - {format_eta(end_sec)}"

    active_downloads[download_id] = {
        "id": download_id,
        "title": title or f"{platform_name or 'Multi-Media'} Video",
        "thumbnail": thumbnail or "",
        "platform_name": platform_name or "Media",
        "is_clip": is_clip,
        "clip_range": clip_label,
        "status": "starting",
        "percent": 0,
        "speed_str": "Connecting...",
        "eta_str": "--:--",
        "filename": None,
        "download_url": None,
        "error": None
    }

    final_filepath = None

    def progress_hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total > 0 else 0

            speed_val = d.get("speed")
            speed_text = format_speed(speed_val) or clean_ansi(d.get("_speed_str", "Calculating..."))

            eta_val = d.get("eta")
            eta_text = format_eta(eta_val) or clean_ansi(d.get("_eta_str", "--:--"))

            active_downloads[download_id].update({
                "status": "downloading",
                "percent": round(percent, 1),
                "speed_str": speed_text,
                "eta_str": eta_text
            })
        elif status == "finished":
            active_downloads[download_id].update({
                "status": "processing",
                "percent": 100,
                "speed_str": "Converting",
                "eta_str": "Encoding output..."
            })

    def postprocessor_hook(d):
        nonlocal final_filepath
        if d.get("status") == "finished":
            info_dict = d.get("info_dict", {})
            fp = info_dict.get("filepath") or d.get("filepath")
            if fp and os.path.exists(fp):
                final_filepath = fp

    try:
        ydl_opts = get_base_ydl_opts()
        ydl_opts['progress_hooks'] = [progress_hook]
        ydl_opts['postprocessor_hooks'] = [postprocessor_hook]

        # Template naming: add clip indicator if clipped
        if is_clip:
            safe_clip = f"[Clip {format_eta(start_sec).replace(':', '-')}-{format_eta(end_sec).replace(':', '-')}]"
            out_template = str(DOWNLOAD_DIR / f"%(title).120s {safe_clip} [%(id)s].%(ext)s")
            ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)])
            ydl_opts['force_keyframes_at_cuts'] = True
        else:
            out_template = str(DOWNLOAD_DIR / "%(title).150s [%(id)s].%(ext)s")

        ydl_opts['outtmpl'] = out_template

        if quality == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif quality == "best":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        else:
            try:
                res_num = int(quality)
                ydl_opts['format'] = f'bestvideo[height<={res_num}]+bestaudio/best[height<={res_num}]/bestvideo+bestaudio/best'
            except ValueError:
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'

        info = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Robust filename resolution after download & FFmpeg post-processing
        resolved_file = None

        # 1. Check if postprocessor hook detected the completed file
        if final_filepath and os.path.exists(final_filepath):
            resolved_file = final_filepath

        # 2. Check requested_downloads dict from yt-dlp
        if not resolved_file and info:
            for req in info.get("requested_downloads", []):
                fp = req.get("filepath") or req.get("_filename")
                if fp and os.path.exists(fp):
                    resolved_file = fp
                    break

        # 3. Check prepare_filename with target extensions
        if not resolved_file and info:
            try:
                prep = ydl.prepare_filename(info)
                if prep and os.path.exists(prep):
                    resolved_file = prep
                else:
                    base_prep, _ = os.path.splitext(prep)
                    for ext in [".mp3", ".mp4", ".m4a", ".webm", ".mkv"]:
                        candidate = base_prep + ext
                        if os.path.exists(candidate):
                            resolved_file = candidate
                            break
            except Exception:
                pass

        # 4. Search DOWNLOAD_DIR for any file containing video ID
        video_id = info.get("id") if info else ""
        if not resolved_file and video_id:
            candidates = [
                f for f in DOWNLOAD_DIR.glob("*")
                if video_id in f.name and not f.name.endswith((".part", ".ytdl")) and f.is_file()
            ]
            if candidates:
                candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                resolved_file = str(candidates[0])

        # 5. Fallback: newest completed file in DOWNLOAD_DIR within last 3 minutes
        if not resolved_file:
            now = time.time()
            recent_files = [
                f for f in DOWNLOAD_DIR.glob("*")
                if f.is_file() and not f.name.endswith((".part", ".ytdl", ".gitkeep")) and (now - f.stat().st_mtime) < 180
            ]
            if recent_files:
                recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                resolved_file = str(recent_files[0])

        if not resolved_file or not os.path.exists(resolved_file):
            raise FileNotFoundError("Could not locate final converted media file on disk.")

        actual_filename = os.path.basename(resolved_file)
        active_downloads[download_id].update({
            "status": "completed",
            "percent": 100,
            "filename": actual_filename,
            "download_url": f"/api/file/{actual_filename}",
            "speed_str": "Completed",
            "eta_str": "0s"
        })
    except Exception as e:
        err_msg = clean_ansi(str(e))
        if "Sign in to confirm you're not a bot" in err_msg:
            err_msg = "YouTube bot verification triggered on cloud server IP. Add your cookies (via YOUTUBE_COOKIES environment variable or cookies.txt) to enable downloads."
        elif "/s/" in url and ("reddit.com" in url or "redd.it" in url):
            err_msg = "Reddit shortlinks (/s/) cannot be extracted because Reddit redirects them to the subreddit homepage. Please open the post in your browser and copy the full URL (e.g., reddit.com/r/.../comments/...)."
        elif "Account authentication is required" in err_msg and "reddit" in err_msg.lower():
            err_msg = "Reddit has blocked anonymous guest access. Please copy the direct post URL or provide authenticated cookies."
        active_downloads[download_id].update({
            "status": "error",
            "error": err_msg
        })

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = clean_video_url(data.get("url", "").strip())
    quality = data.get("quality", "best")
    title = data.get("title", "")
    thumbnail = data.get("thumbnail", "")
    platform_name = data.get("platform_name", "")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400

    download_id = str(uuid.uuid4())[:8]
    thread = threading.Thread(
        target=run_download_task,
        args=(download_id, url, quality, title, thumbnail, platform_name, start_time, end_time),
        daemon=True
    )
    thread.start()

    return jsonify({"success": True, "download_id": download_id})

@app.route("/api/progress/<download_id>", methods=["GET"])
def get_progress(download_id):
    item = active_downloads.get(download_id)
    if not item:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True, "data": item})

@app.route("/api/downloads", methods=["GET"])
def list_downloads():
    files = []
    for item in DOWNLOAD_DIR.glob("*"):
        if item.is_file() and not item.name.endswith(".part") and not item.name.endswith(".ytdl") and item.name != ".gitkeep":
            try:
                stat = item.stat()
                size_mb = stat.st_size / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb/1024:.2f} GB"
                files.append({
                    "name": item.name,
                    "size": size_str,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "ext": item.suffix.lstrip(".").lower(),
                    "download_url": f"/api/file/{item.name}"
                })
            except Exception:
                pass
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"success": True, "files": files, "download_path": str(DOWNLOAD_DIR.resolve())})

@app.route("/api/file/<path:filename>", methods=["GET"])
def get_file(filename):
    """
    Serves the downloaded media file with smart resolution if extension was converted (e.g. .webm -> .mp3).
    """
    file_path = DOWNLOAD_DIR / filename
    
    # 1. Exact match exists
    if file_path.is_file():
        return send_from_directory(str(DOWNLOAD_DIR), filename, as_attachment=True, download_name=filename)
    
    # 2. Match by alternating extension (.mp3, .mp4, etc.)
    base_name, _ = os.path.splitext(filename)
    for alt_ext in [".mp3", ".mp4", ".m4a", ".webm", ".mkv"]:
        alt_path = DOWNLOAD_DIR / f"{base_name}{alt_ext}"
        if alt_path.is_file():
            return send_from_directory(str(DOWNLOAD_DIR), alt_path.name, as_attachment=True, download_name=alt_path.name)
            
    # 3. Match by video ID inside bracket [video_id]
    bracket_match = re.search(r'\[([a-zA-Z0-9_-]+)\]', filename)
    if bracket_match:
        vid_id = bracket_match.group(1)
        candidates = [
            f for f in DOWNLOAD_DIR.glob("*")
            if vid_id in f.name and not f.name.endswith((".part", ".ytdl")) and f.is_file()
        ]
        if candidates:
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            target = candidates[0]
            return send_from_directory(str(DOWNLOAD_DIR), target.name, as_attachment=True, download_name=target.name)

    # 4. If not found, return JSON (so browser doesn't download an HTML 404 error page as .htm)
    return jsonify({"success": False, "error": f"File '{filename}' not found"}), 404

@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Opens folder on local dev machines, or informs users gracefully on web-hosted servers."""
    client_ip = request.remote_addr or ""
    is_local = client_ip in ["127.0.0.1", "::1", "localhost"]
    is_cloud = bool(os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("DYNO"))

    if not is_local or is_cloud:
        return jsonify({
            "success": False,
            "is_remote": True,
            "message": "This site is hosted online! Click 'Save' next to any file in your browser to download it directly to your device."
        })

    try:
        if sys.platform == "win32":
            os.startfile(str(DOWNLOAD_DIR.resolve()))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(DOWNLOAD_DIR.resolve())])
        else:
            subprocess.Popen(["xdg-open", str(DOWNLOAD_DIR.resolve())])
        return jsonify({"success": True, "is_remote": False, "message": "Opened downloads folder."})
    except Exception as e:
        return jsonify({"success": False, "is_remote": False, "error": str(e)}), 500

# Health check endpoint for cloud platforms
@app.route("/healthz")
def healthz():
    return jsonify({"status": "healthy", "service": "media-downloader"}), 200

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))

    # Auto-open browser only when running locally on Windows/Desktop
    if host in ["127.0.0.1", "localhost", "0.0.0.0"] and sys.platform == "win32" and not os.environ.get("NO_BROWSER"):
        import webbrowser
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"==================================================")
    print(f" Multi-Media Downloader running at http://{host}:{port}")
    print(f" Supports: YouTube, TikTok, IG, Twitter/X, FB, Reddit, +1000s")
    print(f" Publishable Web & Production Ready")
    print(f" Download folder: {DOWNLOAD_DIR.resolve()}")
    print(f"==================================================")
    app.run(host=host, port=port, debug=False)
