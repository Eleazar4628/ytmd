import os
import sys
import subprocess
import shutil
import requests

REPO_URL = "https://github.com/Eleazar4628/ytmd.git"
REPO_API_URL = "https://api.github.com/repos/Eleazar4628/ytmd/commits/main"
VERSION_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_version")

def run_upgrade():
    print(f"Verificando actualizaciones en {REPO_URL}...")
    try:
        response = requests.get(REPO_API_URL, timeout=5)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", f"git+{REPO_URL}"], check=True)
            with open(VERSION_FILE, "w") as f:
                f.write(latest_sha)
            print("Actualización completada.")
        else:
            print("No se pudo conectar a GitHub para verificar actualizaciones.")
    except Exception as e:
        print(f"Error al actualizar: {e}")

def check_for_updates_silently():
    try:
        response = requests.get(REPO_API_URL, timeout=2)
        if response.status_code == 200:
            latest_sha = response.json()['sha']
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    if f.read().strip() != latest_sha:
                        print("Nueva versión disponible. Usa 'ytmd --upgrade' para actualizar.")
    except:
        pass

def get_music_folder():
    if os.name == 'nt':
        try:
            import ctypes
            from ctypes import windll, wintypes
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_byte * 8)
                ]

                def __init__(self, uuid_str):
                    u = UUID(uuid_str)
                    ctypes.Structure.__init__(self)
                    self.Data1, self.Data2, self.Data3, self.Data4[0], self.Data4[1], rest = u.fields
                    for i in range(2, 8):
                        self.Data4[i] = rest >> (8 * (5 - (i - 2))) & 0xff

            FOLDERID_Music = GUID("4bd8d571-6d19-48d3-be97-422220080e43")

            SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_wchar_p)
            ]

            path_ptr = ctypes.c_wchar_p()
            result = SHGetKnownFolderPath(ctypes.byref(FOLDERID_Music), 0, None, ctypes.byref(path_ptr))
            if result == 0:
                path = path_ptr.value
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
        # Fallback si algo falla con la API nativa
        return os.path.join(os.path.expanduser("~"), "Music")
    else:
        return "/sdcard/Music" if os.path.exists("/sdcard") else os.path.expanduser("~/storage/music")

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
        print("\nYTMD - YouTube Music Downloader")
        print("usage: ytmd <URL> or ytmd --upgrade")
        return

    arg = sys.argv[1].lower()
    if arg in ["--upgrade", "-u"]:
        run_upgrade()
        return

    check_for_updates_silently()
    check_ffmpeg()
    
    url = sys.argv[1]

    base_path = get_music_folder()

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
        "-o", output_template,
        "--print", "after_move:filepath",
        url
    ]

    try:
        print(f"Iniciando descarga...")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout, end="")  # muestra el progreso normal de yt-dlp

        # La última línea no vacía es la ruta impresa por --print after_move:filepath
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        final_path = lines[-1] if lines else base_path

        print(f"\nDescarga completada: {final_path}")
    except subprocess.CalledProcessError as e:
        print(e.stdout, end="")
        print(e.stderr, end="")
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
