# 🎵 ytmd (YouTube Music Downloader)

Un script automatizado para descargar música de YouTube Music con la mejor calidad disponible, organizada automáticamente por carpetas de Artista y Álbum.

## ✨ Características
- **Auto-actualización:** El script verifica si hay cambios en GitHub y se actualiza solo.
- **Auto-instalación de dependencias:** Detecta si falta FFmpeg e intenta instalarlo (vía Winget en Windows o Pkg en Termux).
- **Organización inteligente:** Crea carpetas siguiendo el patrón `Música/Artista/Álbum/Canción.mp3`.
- **Metadatos completos:** Incluye carátula (convertida a JPG), artista, álbum y títulos oficiales.

## 📥 Instalación

Asegúrate de tener Python instalado y ejecuta el siguiente comando en tu terminal (CMD, PowerShell o Termux):

```bash
pip install git+[https://github.com/Eleazar4628/ytmd.git](https://github.com/Eleazar4628/ytmd.git)