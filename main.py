import os
import re
import uuid
import asyncio
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yt_dlp


# ── Directorio temporal para los MP3 generados ──────────────────────────────
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "yt_mp3_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Limpieza de archivos al apagar el servidor
    for f in DOWNLOAD_DIR.glob("*.mp3"):
        try:
            f.unlink()
        except Exception:
            pass


app = FastAPI(title="YT MP3 Downloader", lifespan=lifespan)


# ── Modelos ──────────────────────────────────────────────────────────────────
class DownloadRequest(BaseModel):
    url: str


class VideoInfo(BaseModel):
    title: str
    duration: str
    thumbnail: str
    channel: str


# ── Utilidades ───────────────────────────────────────────────────────────────
def segundos_a_duracion(segundos: int) -> str:
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def es_url_valida(url: str) -> bool:
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", url))


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/info")
async def get_video_info(req: DownloadRequest) -> VideoInfo:
    """Obtiene metadatos del video antes de descargar."""
    if not es_url_valida(req.url):
        raise HTTPException(status_code=400, detail="URL de YouTube no válida.")

    opts = {"quiet": True, "skip_download": True, "noplaylist": True}

    try:
        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(req.url, download=False)

        info = await loop.run_in_executor(None, _extract)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo obtener info del video: {e}")

    return VideoInfo(
        title=info.get("title", "Sin título"),
        duration=segundos_a_duracion(info.get("duration", 0)),
        thumbnail=info.get("thumbnail", ""),
        channel=info.get("uploader", "Desconocido"),
    )


@app.post("/download")
async def download_mp3(req: DownloadRequest):
    """Descarga el audio del video y devuelve el archivo MP3."""
    if not es_url_valida(req.url):
        raise HTTPException(status_code=400, detail="URL de YouTube no válida.")

    file_id = uuid.uuid4().hex
    output_template = str(DOWNLOAD_DIR / f"{file_id}.%(ext)s")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",
        }],
    }

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(req.url, download=True)
                return info.get("title", "audio")

        title = await loop.run_in_executor(None, _download)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la descarga: {e}")

    mp3_path = DOWNLOAD_DIR / f"{file_id}.mp3"
    if not mp3_path.exists():
        raise HTTPException(status_code=500, detail="El archivo MP3 no se generó correctamente.")

    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)

    return FileResponse(
        path=str(mp3_path),
        media_type="audio/mpeg",
        filename=f"{safe_title}.mp3",
        background=None,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
