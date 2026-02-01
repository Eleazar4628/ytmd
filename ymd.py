import os
import sys
import subprocess
import shutil
import requests

# Configuración del proyecto ymd
REPO_URL = "https://github.com/Eleazar4628/ytmd.git"
REPO_API_URL = "https://api.github.com/repos/Eleazar4628/ytmd/commits/main"
VERSION_FILE = os.path.join(os.path.expanduser("~"), ".ymd_version")

def run_upgrade():
    """Actualiza el script y el registro de versión local."""
    print(f"Checking for updates at {REPO_URL}...")
    try:
        response = requests.get(REPO_API_URL, timeout=5)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            # Actualización vía pip
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", f"git+{REPO_URL}"], check=True)
            # Guardar hash para evitar avisos constantes
            with open(VERSION_FILE, "w") as f:
                f.write(latest_sha)
            print("✅ Successfully upgraded to the latest version.")
        else:
            print("❌ Connection to GitHub failed. Check your internet.")
    except Exception as e:
        print(f"❌ Upgrade failed: {e}")

def check_for_updates_silently():
    """Verifica si hay una nueva versión sin detener el programa."""
    try:
        response = requests.get(REPO_API_URL, timeout=2)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    if f.read().strip() != latest_sha:
                        print("💡 New version available! Use 'ymd --upgrade' to update.")
    except:
        pass

def check_ffmpeg():
    """Verifica la presencia de FFmpeg e intenta instalarlo si falta."""
    if shutil.which("ffmpeg") is None:
        print("📦 FFmpeg not found.")
        choice = input("Install it now? (y/n): ").lower()
        if choice == 'y':
            try:
                if os.name == 'nt':
                    subprocess.run(["winget", "install", "ffmpeg"], check=True)
                else:
                    subprocess.run(["pkg", "install", "ffmpeg", "-y"], check=True)
                print("✅ Installed. Please restart your terminal.")
                sys.exit(0)
            except Exception as e:
                print(f"❌ Auto-install failed: {e}. Please install FFmpeg manually.")
                sys.exit(1)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("\n🎵 ymd - YouTube Music Downloader")
        print("Usage: ymd <URL> or ymd --upgrade")
        return

    arg = sys.argv[1].lower()
    
    # Manejo de actualización manual
    if arg in ["--upgrade", "-u"]:
        run_upgrade()
        return

    # Proceso de descarga
    check_for_updates_silently()
    check_ffmpeg()
    
    url = sys.argv[1]

    # Determinación de rutas según SO
    if os.name == 'nt': 
        base_path = os.path.join(os.path.expanduser("~"), "Music")
    else: 
        # Path estándar para Termux/Android
        base_path = "/sdcard/Music" if os.path.exists("/sdcard") else os.path.expanduser("~/storage/music")

    # Estructura de carpetas: Artista/Álbum/Canción.mp3
    output_template = os.path.join(base_path, "%(artist,uploader)s", "%(album,playlist_title,Unknown_Album)s", "%(title)s.%(ext)s")

    command = [
        "yt-dlp",
        "-f", "ba",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--embed-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails", "jpg",
        # Recorte inteligente de carátula a 1:1 (cuadrado)
        "--ppa", "ThumbnailsConvertor:-vf crop=ih:ih",
        # Limpieza de títulos (Quita "Official Video", "HD", etc.)
        "--parse-metadata", "title:%(title)s",
        "--replace-in-metadata", "title", r"(?i)\s*([\(\[][^\]\)]*(video|audio|lyrics|official|video oficial|hd)[^\]\)]*[\)\]])", "",
        "-o", output_template,
        url
    ]

    try:
        print(f"🚀 Processing download...")
        subprocess.run(command, check=True)
        print(f"\n✨ Done! Music saved in: {base_path}")
    except Exception as e:
        print(f"\n❌ Download failed: {e}")

if __name__ == "__main__":
    main()