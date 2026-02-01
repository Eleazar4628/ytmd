import os
import sys
import subprocess
import shutil
import requests

REPO_URL = "https://github.com/Eleazar4628/ytmd.git"
REPO_API_URL = "https://api.github.com/repos/Eleazar4628/ytmd/commits/main"
VERSION_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_version")

def run_upgrade():
    print(f"Checking for updates from {REPO_URL}...")
    try:
        response = requests.get(REPO_API_URL, timeout=5)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", f"git+{REPO_URL}"], check=True)
            with open(VERSION_FILE, "w") as f:
                f.write(latest_sha)
            print("✅ Successfully upgraded to the latest version of ytmd.")
        else:
            print("❌ Could not connect to GitHub to check for updates.")
    except Exception as e:
        print(f"❌ Upgrade failed: {e}")

def check_for_updates_silently():
    try:
        response = requests.get(REPO_API_URL, timeout=2)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    if f.read().strip() != latest_sha:
                        print("💡 A new version is available. Use 'ytmd --upgrade' to update.")
    except:
        pass

def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("📦 FFmpeg not found.")
        choice = input("Install now? (y/n): ").lower()
        if choice == 'y':
            if os.name == 'nt':
                subprocess.run(["winget", "install", "ffmpeg"], check=True)
            else:
                subprocess.run(["pkg", "install", "ffmpeg", "-y"], check=True)
            print("✅ Installed. Please restart your terminal.")
            sys.exit(0)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("\n🎵 ytmd - YouTube Music Downloader")
        print("Usage: ytmd <URL> or ytmd --upgrade")
        return

    arg = sys.argv[1].lower()
    if arg in ["--upgrade", "-u"]:
        run_upgrade()
        return

    check_for_updates_silently()
    check_ffmpeg()
    
    url = sys.argv[1]

    if os.name == 'nt': 
        base_path = os.path.join(os.path.expanduser("~"), "Music")
    else: 
        base_path = "/sdcard/Music" if os.path.exists("/sdcard") else os.path.expanduser("~/storage/music")

    output_template = os.path.join(base_path, "%(artist,uploader)s", "%(album,playlist_title,Unknown_Album)s", "%(title)s.%(ext)s")

    command = [
        "yt-dlp", "-f", "ba", "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--embed-metadata", "--embed-thumbnail", "--convert-thumbnails", "jpg",
        "--ppa", "ThumbnailsConvertor:-vf crop=ih:ih",
        "--parse-metadata", "upload_date:%(date)s",
        "--replace-in-metadata", "date", r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3",
        "--parse-metadata", "artist:%(artist)s",
        "--replace-in-metadata", "artist", r",.*", "",
        "--replace-in-metadata", "artist", r" &.*", "",
        "--parse-metadata", "title:%(title)s",
        "--replace-in-metadata", "title", r"(?i)\s*([\(\[][^\]\)]*(video|audio|lyrics|official|video oficial|hd)[^\]\)]*[\)\]])", "",
        "-o", output_template, url
    ]

    try:
        print(f"🚀 Initializing download...")
        subprocess.run(command, check=True)
        print(f"\n✨ Done! Saved in: {base_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()