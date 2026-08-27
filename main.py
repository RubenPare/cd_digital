"""
CD Digital - Reproductor de disco para fans
Version liviana: el APK no trae los mp3, los descarga del servidor
la primera vez que cada tema se reproduce y los guarda en cache local.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.audio import SoundLoader
from kivy.clock import mainthread
from kivy.properties import StringProperty, BooleanProperty
from kivy.lang import Builder
import os
import sys
import threading
import requests

def resource_path(nombre_archivo):
    """Devuelve la ruta correcta al archivo, tanto corriendo con python main.py
    como empaquetado en un .exe con PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, nombre_archivo)
    return os.path.join(os.path.abspath("."), nombre_archivo)

Builder.load_file(resource_path("player.kv"))

# --------------------------------------------------------------------
# CONFIGURACION - apunta esto a tu servidor FastAPI
# --------------------------------------------------------------------
SERVER_URL = "https://cd-digital-server.onrender.com"
API_KEY = "cambiar-esta-clave-123"

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cd_digital_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
# --------------------------------------------------------------------


class TrackItem(BoxLayout):
    titulo = StringProperty("")
    track_id = StringProperty("")


class PlayerScreen(Screen):
    pass


class CDDigitalApp(App):
    sound = None
    current_track_id = StringProperty("")
    is_playing = BooleanProperty(False)
    tracks = []

    def build(self):
        self.title = "CD Digital"
        self.sm = ScreenManager()
        self.player_screen = PlayerScreen(name="player")
        self.sm.add_widget(self.player_screen)

        self.player_screen.ids.status_label.text = "Cargando disco..."
        threading.Thread(target=self.cargar_tracklist, daemon=True).start()
        return self.sm

    def cargar_tracklist(self):
        try:
            r = requests.get(
                f"{SERVER_URL}/tracks",
                headers={"x-api-key": API_KEY},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            self.tracks = data["tracks"]
            self.set_ui_disco(data["banda"], data["disco"])
        except Exception as e:
            self.set_status(f"No se pudo conectar al servidor: {e}")

    @mainthread
    def set_ui_disco(self, banda, disco):
        root = self.player_screen.ids
        root.banda_label.text = banda
        root.disco_label.text = disco
        root.tracklist_box.clear_widgets()

        for t in self.tracks:
            item = TrackItem()
            item.titulo = t["titulo"]
            item.track_id = t["id"]
            item.ids.track_btn.bind(
                on_release=lambda btn, tid=t["id"]: self.play_track(tid)
            )
            root.tracklist_box.add_widget(item)

        self.set_status("Elegi un tema para reproducir")
        self.cargar_caratula()

    def cargar_caratula(self):
        threading.Thread(target=self._descargar_caratula, daemon=True).start()

    def _descargar_caratula(self):
        cache_path = os.path.join(CACHE_DIR, "caratula.jpg")
        if not os.path.exists(cache_path):
            try:
                r = requests.get(
                    f"{SERVER_URL}/caratula",
                    headers={"x-api-key": API_KEY},
                    timeout=60,
                )
                if r.status_code == 200:
                    with open(cache_path, "wb") as f:
                        f.write(r.content)
            except Exception:
                return
        if os.path.exists(cache_path):
            self.set_caratula(cache_path)

    @mainthread
    def set_caratula(self, path):
        self.player_screen.ids.caratula_img.source = path

    @mainthread
    def set_status(self, texto):
        self.player_screen.ids.status_label.text = texto

    def play_track(self, track_id):
        cache_path = os.path.join(CACHE_DIR, f"{track_id}.mp3")

        if os.path.exists(cache_path):
            self._reproducir_desde_cache(track_id, cache_path)
        else:
            self.set_status("Descargando tema...")
            threading.Thread(
                target=self._descargar_y_reproducir, args=(track_id, cache_path), daemon=True
            ).start()

    def _descargar_y_reproducir(self, track_id, cache_path):
        try:
            r = requests.get(
                f"{SERVER_URL}/audio/{track_id}",
                headers={"x-api-key": API_KEY},
                timeout=60,
                stream=True,
            )
            r.raise_for_status()
            tmp_path = cache_path + ".part"
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            os.replace(tmp_path, cache_path)
            self._reproducir_desde_cache(track_id, cache_path)
        except Exception as e:
            self.set_status(f"Error al descargar: {e}")

    @mainthread
    def _reproducir_desde_cache(self, track_id, cache_path):
        if self.sound:
            self.sound.stop()
            self.sound.unload()

        self.sound = SoundLoader.load(cache_path)
        if self.sound:
            self.sound.play()
            self.current_track_id = track_id
            self.is_playing = True
            titulo = next((t["titulo"] for t in self.tracks if t["id"] == track_id), track_id)
            self.set_status(f"Reproduciendo: {titulo}")
            self.sound.bind(on_stop=lambda *_: self.on_track_finished())

    def toggle_play_pause(self):
        if not self.sound:
            if self.tracks:
                self.play_track(self.tracks[0]["id"])
            return
        if self.is_playing:
            self.sound.stop()
            self.is_playing = False
        else:
            self.sound.play()
            self.is_playing = True

    def next_track(self):
        ids = [t["id"] for t in self.tracks]
        if not ids:
            return
        i = ids.index(self.current_track_id) if self.current_track_id in ids else -1
        self.play_track(ids[(i + 1) % len(ids)])

    def prev_track(self):
        ids = [t["id"] for t in self.tracks]
        if not ids:
            return
        i = ids.index(self.current_track_id) if self.current_track_id in ids else 0
        self.play_track(ids[(i - 1) % len(ids)])

    def on_track_finished(self):
        if self.is_playing:
            self.next_track()


if __name__ == "__main__":
    CDDigitalApp().run()