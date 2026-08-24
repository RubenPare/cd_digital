from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
import os

app = FastAPI(title="CD Digital - Servidor")

AUDIO_DIR = "audio"
API_KEY = "cambiar-esta-clave-123"

NOMBRE_BANDA = "Nombre de la Banda"
NOMBRE_DISCO = "Nombre del Disco"

TRACKLIST = [
    {"id": "track01", "titulo": "01 - Tema Uno", "archivo": "track01.mp3"},
    {"id": "track02", "titulo": "02 - Tema Dos", "archivo": "track02.mp3"},
    {"id": "track03", "titulo": "03 - Tema Tres", "archivo": "track03.mp3"},
]


def verificar_key(x_api_key):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")


@app.get("/tracks")
def get_tracks(x_api_key: str = Header(default=None)):
    verificar_key(x_api_key)
    return {
        "banda": NOMBRE_BANDA,
        "disco": NOMBRE_DISCO,
        "tracks": [{"id": t["id"], "titulo": t["titulo"]} for t in TRACKLIST],
    }


@app.get("/audio/{track_id}")
def get_audio(track_id: str, x_api_key: str = Header(default=None)):
    verificar_key(x_api_key)
    track = next((t for t in TRACKLIST if t["id"] == track_id), None)
    if not track:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    path = os.path.join(AUDIO_DIR, track["archivo"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no disponible en el servidor")
    return FileResponse(path, media_type="audio/mpeg", filename=track["archivo"])


@app.get("/caratula")
def get_caratula(x_api_key: str = Header(default=None)):
    verificar_key(x_api_key)
    path = os.path.join(AUDIO_DIR, "..", "caratula.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Carátula no disponible")
    return FileResponse(path, media_type="image/jpeg")