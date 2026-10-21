import os
import sys
import time
import subprocess
import shutil
import json
import re
import requests
from urllib.parse import urlparse, parse_qs
from colorama import init, Fore, Style

init()

REPO_URL = "https://github.com/Eleazar4628/ytmd.git"
REPO_API_URL = "https://api.github.com/repos/Eleazar4628/ytmd/commits/main"
VERSION_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_version")
RETRY_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_retry.json")
LAST_LOG_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_last.log")
DEPENDENCY_CHECK_FILE = os.path.join(os.path.expanduser("~"), ".ytmd_dependencies_last_check_v2")
DEPENDENCY_CHECK_INTERVAL = 60 * 60 * 24


def get_latest_sha(timeout=5, retries=2, silent=False):
    """Consulta el SHA del último commit en GitHub, con reintentos y manejo de rate-limit."""
    for attempt in range(retries + 1):
        try:
            response = requests.get(REPO_API_URL, timeout=timeout)
            if response.status_code == 200:
                return response.json()['sha']
            if response.status_code == 403 and response.headers.get('X-RateLimit-Remaining') == '0':
                if not silent:
                    print("\nLímite de solicitudes a GitHub alcanzado. Probá de nuevo más tarde.")
                return None
        except requests.exceptions.RequestException:
            pass
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    if not silent:
        print("No se pudo conectar a GitHub para verificar actualizaciones.")
    return None


def run_upgrade():
    print(f"Verificando actualizaciones en {REPO_URL}...")
    latest_sha = get_latest_sha(silent=False)
    if latest_sha is None:
        return
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", f"git+{REPO_URL}"], check=True)
        with open(VERSION_FILE, "w") as f:
            f.write(latest_sha)
        print("Actualización completada.")
    except subprocess.CalledProcessError as e:
        print(f"Error al actualizar: {e}")


def check_for_updates_silently():
    latest_sha = get_latest_sha(timeout=2, retries=0, silent=True)
    if latest_sha and os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            if f.read().strip() != latest_sha:
                print("Nueva versión disponible. Usa 'ytmd --upgrade' para actualizar.")


def update_dependencies_if_needed():
    """Actualiza diariamente las dependencias Python y herramientas instaladas."""
    now = time.time()
    if os.path.exists(DEPENDENCY_CHECK_FILE):
        try:
            last_check = float(open(DEPENDENCY_CHECK_FILE).read().strip())
            if now - last_check < DEPENDENCY_CHECK_INTERVAL:
                return
        except (ValueError, OSError):
            pass

    # Mantiene al día todas las dependencias declaradas en setup.py y yt-dlp.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade",
         "yt-dlp[default]", "requests", "colorama"],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    tools_to_update = []
    if shutil.which("ffmpeg"):
        tools_to_update.append(("ffmpeg", "Gyan.FFmpeg.Shared", "ffmpeg"))
    if shutil.which("node"):
        tools_to_update.append(("node", "OpenJS.NodeJS.LTS", "nodejs"))

    if os.name == "nt" and shutil.which("winget"):
        for _tool, package_id, _termux_name in tools_to_update:
            subprocess.run(
                ["winget", "upgrade", "--id", package_id, "--exact",
                 "--silent", "--accept-source-agreements",
                 "--accept-package-agreements"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    elif os.path.exists("/data/data/com.termux/files/usr"):
        for _tool, _package_id, termux_name in tools_to_update:
            subprocess.run(
                ["pkg", "upgrade", "-y", termux_name],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

    try:
        with open(DEPENDENCY_CHECK_FILE, "w") as f:
            f.write(str(now))
    except OSError:
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
        return os.path.join(os.path.expanduser("~"), "Music")
    else:
        return "/sdcard/Music" if os.path.exists("/sdcard") else os.path.expanduser("~/storage/music")


def check_dependencies():
    missing = []
    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if not missing:
        return
    print(f"Falta(n) dependencia(s): {', '.join(missing)}")
    print("Instalá con:")
    for dep in missing:
        if dep == "yt-dlp":
            print("  pip install -U yt-dlp")
        else:
            if os.name == 'nt':
                print("  winget install ffmpeg")
            else:
                print("  pkg install ffmpeg -y  # Termux")
    sys.exit(1)


def clean_url(url):
    """Limpia espacios y barras finales sobrantes que rompen el parseo de yt-dlp
    (por ejemplo, URLs de playlist copiadas con un '/' extra al final del query,
    tipo '?list=ID/', que hace que YouTube devuelva 404/400)."""
    url = url.strip()
    url = url.rstrip('/')
    return url


def to_music_youtube(url):
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        video_id = None
        if "youtu.be" in host:
            video_id = parsed.path.strip("/").split("/")[0]
        elif "youtube.com" in host:
            qs = parse_qs(parsed.query)
            if "v" in qs:
                video_id = qs["v"][0]
        if video_id and len(video_id) == 11:
            new_url = f"https://music.youtube.com/watch?v={video_id}"
            if new_url != url:
                print(f"Redirigiendo a YT Music: {new_url}")
                return new_url
    except Exception:
        pass
    return url


PATH_MARKER = "___YTMD_FILEPATH___"
RETRY_ITEM_MARKER = "___YTMD_RETRY_ITEM___"


def open_download_folder(path):
    """Abre una carpeta en el explorador de archivos del sistema."""
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif os.path.exists("/sdcard"):  # Termux/Android
            subprocess.run(["termux-open", path], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


def is_playlist_url(url):
    query = parse_qs(urlparse(url).query)
    return "list" in query and "v" not in query


def load_retry_urls():
    try:
        with open(RETRY_FILE, "r", encoding="utf-8") as f:
            urls = json.load(f)
        valid_urls = {
            url for url in urls
            if isinstance(url, str) and url and not is_playlist_url(url)
        }
        if valid_urls != set(urls):
            save_retry_urls(valid_urls)
        return valid_urls
    except (OSError, ValueError, TypeError):
        return set()


def save_retry_urls(urls):
    try:
        with open(RETRY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(urls), f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"No se pudo guardar la lista de reintentos: {e}")


def build_download_command(url):
    base_path = get_music_folder()
    output_template = os.path.join(
        base_path, "%(artist,uploader)s",
        "%(album,playlist_title,Unknown_Album)s", "%(title)s.%(ext)s"
    )
    command = [
        "yt-dlp", "--ignore-config", "--verbose", "--ignore-errors",
        "-f", "ba", "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--force-overwrites",
        "--embed-metadata", "--embed-thumbnail", "--convert-thumbnails", "jpg",
        "--postprocessor-args", "ThumbnailsConvertor:-vf crop=ih:ih",
        "--parse-metadata", "upload_date:%(date)s",
        "--replace-in-metadata", "date", r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3",
        "--parse-metadata", "artist:%(artist)s",
        "--replace-in-metadata", "artist", r",.*", "",
        "--replace-in-metadata", "artist", r" &.*", "",
        "--parse-metadata", "artist:%(meta_album_artist)s",
        "--parse-metadata", "title:%(title)s",
        "--replace-in-metadata", "title",
        r"(?i)\s*([\(\[][^\]\)]*(video|audio|lyrics|official|video oficial|hd)[^\]\)]*[\)\]])", "",
        "--parse-metadata", ":(?P<meta_comment>)",
        "--print", f"before_dl:{RETRY_ITEM_MARKER}%(webpage_url)s",
        "--print", f"after_move:{PATH_MARKER}%(filepath)s",
        "-o", output_template,
    ]
    if shutil.which("node"):
        command.extend(["--js-runtimes", "node"])
    command.append(url)
    return command


def run_download(command, original_url=None):
    """Ejecuta yt-dlp mostrando y guardando el log, y registra canciones fallidas."""
    output_dirs = []
    failed_urls = load_retry_urls()
    current_url = original_url
    saw_error = False
    log_line_count = 0
    print(f"Log completo: {LAST_LOG_FILE}")
    with open(LAST_LOG_FILE, "w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1
        )
        for line in process.stdout:
            line = line.rstrip("\r\n")
            log_file.write(line + "\n")
            log_file.flush()
            log_line_count += 1
            if line.startswith(PATH_MARKER):
                filepath = line[len(PATH_MARKER):].strip()
                if filepath:
                    output_dirs.append(os.path.dirname(filepath))
                if current_url in failed_urls:
                    failed_urls.discard(current_url)
                    save_retry_urls(failed_urls)
                continue

            if line.startswith(RETRY_ITEM_MARKER):
                current_url = line[len(RETRY_ITEM_MARKER):].strip()
            else:
                if "Downloading item " in line:
                    current_url = None
                match = re.search(r"Extracting URL:\s*(\S+)", line)
                if match:
                    current_url = match.group(1)

            print(line, flush=True)
            if re.search(r"\bERROR:", line, re.IGNORECASE):
                saw_error = True
                if current_url:
                    failed_urls.add(current_url)
                    save_retry_urls(failed_urls)

        process.wait()

    if process.returncode != 0:
        if original_url and not saw_error and not is_playlist_url(original_url):
            failed_urls.add(original_url)
            save_retry_urls(failed_urls)
        if log_line_count == 0:
            print("yt-dlp terminó sin escribir ninguna línea al log.")
            print(f"Ejecutable: {shutil.which('yt-dlp') or 'no encontrado'}")
            print("Comando: " + subprocess.list2cmdline(command))
        raise subprocess.CalledProcessError(process.returncode, command)

    seen = set()
    unique_dirs = []
    for directory in output_dirs:
        if directory not in seen:
            seen.add(directory)
            unique_dirs.append(directory)
    return unique_dirs


def run_retry():
    urls = sorted(load_retry_urls())
    if not urls:
        print("No hay canciones pendientes para reintentar.")
        return

    print(f"Reintentando {len(urls)} URL(s)...")
    for url in urls:
        print(f"\nReintentando: {url}")
        try:
            output_dirs = run_download(build_download_command(url), original_url=url)
            for folder in output_dirs:
                open_download_folder(folder)
        except subprocess.CalledProcessError:
            print(f"El reintento falló; queda guardado: {url}")

    remaining = load_retry_urls()
    if remaining:
        print(f"Quedan {len(remaining)} URL(s) pendientes. Ejecuta ytmd -retry para volver a intentarlo.")
    else:
        print("Todas las canciones pendientes se descargaron correctamente.")


def main():
    if len(sys.argv) < 2:
        print("\nYTMD - YouTube Music Downloader")
        print("usage: ytmd <URL> | ytmd --upgrade | ytmd -retry")
        return

    arg = sys.argv[1].lower()
    if arg in ["--upgrade", "-u"]:
        run_upgrade()
        return

    check_for_updates_silently()
    update_dependencies_if_needed()
    check_dependencies()

    if arg in ["--retry", "-retry"]:
        run_retry()
        return

    url = to_music_youtube(clean_url(sys.argv[1]))

    try:
        print("\nIniciando descarga...\n")
        output_dirs = run_download(build_download_command(url), original_url=url)
        print(f"\n{Fore.GREEN}===============================\n       Descarga completa\n==============================={Style.RESET_ALL}\n")
        for folder in output_dirs:
            open_download_folder(folder)
        remaining = load_retry_urls()
        if remaining:
            print(f"\n{len(remaining)} URL(s) con error guardadas para reintento. Usa ytmd -retry.")
    except subprocess.CalledProcessError as e:
        print(f"\nyt-dlp terminó con código {e.returncode}. El log completo aparece arriba.")
        remaining = load_retry_urls()
        if remaining:
            print(f"{len(remaining)} canción(es) con error guardadas para reintento. Usa ytmd -retry.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()