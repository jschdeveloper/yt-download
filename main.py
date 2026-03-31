import os
import re
import uuid
import asyncio
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

import static_ffmpeg
static_ffmpeg.add_paths()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import yt_dlp


DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "yt_mp3_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
COOKIES_FILE = Path(tempfile.gettempdir()) / "yt_cookies.txt"


def setup_cookies():
    cookies_content = os.environ.get("YT_COOKIES", "").strip()
    if cookies_content:
        COOKIES_FILE.write_text(cookies_content, encoding="utf-8")
        print("✅ Cookies de YouTube cargadas.")
        return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_cookies()
    yield
    for f in DOWNLOAD_DIR.glob("*.mp3"):
        try:
            f.unlink()
        except Exception:
            pass


app = FastAPI(title="YT MP3 Downloader", lifespan=lifespan)


class DownloadRequest(BaseModel):
    url: str


class VideoInfo(BaseModel):
    title: str
    duration: str
    thumbnail: str
    channel: str


def segundos_a_duracion(segundos: int) -> str:
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def es_url_valida(url: str) -> bool:
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", url))


# Diferentes estrategias de extracción, en orden de preferencia
PLAYER_STRATEGIES = [
    ["tv_embedded"],        # Cliente TV — menos bloqueado en datacenters
    ["android"],            # App Android
    ["android", "web"],     # Android + web fallback
    ["mweb"],               # YouTube móvil web
]


def get_ydl_opts(strategy: list, extra: dict = {}) -> dict:
    opts = {
        "quiet": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": strategy,
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 12; Pixel 6) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/112.0.0.0 Mobile Safari/537.36"
            )
        },
    }
    if COOKIES_FILE.exists():
        opts["cookiefile"] = str(COOKIES_FILE)
    opts.update(extra)
    return opts


async def extract_with_fallback(url: str, extra_opts: dict = {}) -> dict:
    """Intenta extraer info probando cada estrategia hasta que una funcione."""
    loop = asyncio.get_event_loop()
    last_error = None

    for strategy in PLAYER_STRATEGIES:
        opts = get_ydl_opts(strategy, extra_opts)
        try:
            def _extract(o=opts):
                with yt_dlp.YoutubeDL(o) as ydl:
                    return ydl.extract_info(url, download="outtmpl" in o)

            result = await loop.run_in_executor(None, _extract)
            print(f"✅ Estrategia exitosa: {strategy}")
            return result
        except Exception as e:
            last_error = e
            print(f"⚠️  Estrategia {strategy} falló: {e}")
            continue

    raise last_error


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/info")
async def get_video_info(req: DownloadRequest) -> VideoInfo:
    if not es_url_valida(req.url):
        raise HTTPException(status_code=400, detail="URL de YouTube no válida.")
    try:
        info = await extract_with_fallback(req.url, {"skip_download": True})
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
    if not es_url_valida(req.url):
        raise HTTPException(status_code=400, detail="URL de YouTube no válida.")

    file_id = uuid.uuid4().hex
    output_template = str(DOWNLOAD_DIR / f"{file_id}.%(ext)s")

    extra = {
        "format": "bestaudio/best",
        "format_sort": ["abr", "asr", "acodec"],  # Prioriza audio, acepta cualquier codec
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",
        }],
    }

    try:
        info = await extract_with_fallback(req.url, extra)
        title = info.get("title", "audio")
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
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
