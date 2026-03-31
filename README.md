# 🎵 YT·MP3 — Web App

Interfaz web para descargar audio de YouTube en MP3, construida con **FastAPI** y lista para desplegar en la nube.

---

## 📁 Estructura del proyecto

```
yt-mp3-app/
├── main.py           ← Backend FastAPI
├── index.html        ← Interfaz web
├── requirements.txt  ← Dependencias Python
├── render.yaml       ← Config para deploy en Render
└── README.md
```

---

## 🚀 Deploy en Render (gratis)

### 1. Sube el proyecto a GitHub

```bash
git init
git add .
git commit -m "YT MP3 web app"
git remote add origin https://github.com/TU_USUARIO/yt-mp3-app.git
git push -u origin main
```

### 2. Crea el servicio en Render

1. Ve a [https://render.com](https://render.com) y crea una cuenta gratuita
2. Click en **"New → Web Service"**
3. Conecta tu repositorio de GitHub
4. Render detectará el `render.yaml` automáticamente
5. Click en **"Deploy"**

En ~2 minutos tendrás una URL pública como:
```
https://yt-mp3-downloader.onrender.com
```

> ⚠️ El plan gratuito de Render pone el servicio en "sleep" tras 15 min de inactividad.
> La primera petición puede tardar ~30 segundos en despertar.
> Para uso interno continuo, considera el plan Starter ($7/mes).

---

## 💻 Ejecutar en local (desarrollo)

### Requisitos
- Python 3.10+
- ffmpeg instalado y en el PATH

### Instalación

```bash
pip install -r requirements.txt
```

### Arrancar el servidor

```bash
uvicorn main:app --reload
```

Abre el navegador en: [http://localhost:8000](http://localhost:8000)

---

## 🔌 API Endpoints

| Método | Ruta        | Descripción                                 |
|--------|-------------|---------------------------------------------|
| GET    | `/`         | Sirve la interfaz web                       |
| POST   | `/info`     | Obtiene título, duración y thumbnail        |
| POST   | `/download` | Descarga y devuelve el MP3                  |
| GET    | `/health`   | Health check para el balanceador de Render  |

### Ejemplo `/info`
```bash
curl -X POST https://tu-app.onrender.com/info \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Ejemplo `/download`
```bash
curl -X POST https://tu-app.onrender.com/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
     --output audio.mp3
```

---

## ⚙️ Alternativas de deploy

| Plataforma | Plan gratuito | Notas |
|------------|--------------|-------|
| **Render** | ✅ Sí | Recomendado. ffmpeg disponible. |
| **Railway** | ✅ $5 crédito/mes | Más rápido, fácil de configurar. |
| **Fly.io** | ✅ Sí | Requiere Docker. Más control. |
| **VPS propio** | — | Máximo control, costo fijo. |

---

## 📝 Notas

- Los MP3 generados se almacenan temporalmente en el servidor y se limpian al reiniciar.
- El parámetro `--no-playlist` está activo: siempre descarga solo el video indicado.
- Compatible con Python 3.10, 3.11 y 3.12.
