

"""
CD Digital - Reproductor de disco para fans

La aplicación no trae los MP3 dentro del APK/EXE.
Los descarga del servidor la primera vez que se reproduce
cada tema y los guarda en cache local.
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


# --------------------------------------------------------------------
# RUTA DE RECURSOS
# --------------------------------------------------------------------

def resource_path(nombre_archivo):
    """
    Devuelve la ruta correcta del archivo tanto ejecutando
    con Python como empaquetado con PyInstaller.
    """

    if hasattr(sys, "_MEIPASS"):
        return os.path.join(
            sys._MEIPASS,
            nombre_archivo
        )

    return os.path.join(
        os.path.abspath("."),
        nombre_archivo
    )


# --------------------------------------------------------------------
# CARGAR INTERFAZ
# --------------------------------------------------------------------

Builder.load_file(
    resource_path("player.kv")
)


# --------------------------------------------------------------------
# CONFIGURACION
# --------------------------------------------------------------------

SERVER_URL = "https://cd-digital.onrender.com"

API_KEY = "cambiar-esta-clave-123"


# --------------------------------------------------------------------
# ELEMENTOS DE LA INTERFAZ
# --------------------------------------------------------------------

class TrackItem(BoxLayout):

    titulo = StringProperty("")
    track_id = StringProperty("")


class PlayerScreen(Screen):
    pass


# --------------------------------------------------------------------
# APLICACION
# --------------------------------------------------------------------

class CDDigitalApp(App):

    sound = None

    current_track_id = StringProperty("")

    is_playing = BooleanProperty(False)

    tracks = []

    # Indica si el stop fue provocado manualmente.
    manual_stop = False

    # Información del disco
    banda = StringProperty("")
    disco = StringProperty("")
    descripcion = StringProperty("")


    # ----------------------------------------------------------------
    # INICIO
    # ----------------------------------------------------------------

    def build(self):

        self.cache_dir = os.path.join(
            self.user_data_dir,
            ".cd_digital_cache"
        )

        os.makedirs(
            self.cache_dir,
            exist_ok=True
        )

        self.title = "CD Digital"

        self.sm = ScreenManager()

        self.player_screen = PlayerScreen(
            name="player"
        )

        self.sm.add_widget(
            self.player_screen
        )

        self.player_screen.ids.status_label.text = (
            "Cargando disco..."
        )

        threading.Thread(
            target=self.cargar_tracklist,
            daemon=True
        ).start()

        return self.sm


    # ----------------------------------------------------------------
    # CARGAR INFORMACION DEL DISCO
    # ----------------------------------------------------------------

    def cargar_tracklist(self):

        try:

            print("======================================")
            print("CONECTANDO CON EL SERVIDOR")
            print(SERVER_URL)
            print("======================================")

            r = requests.get(
                f"{SERVER_URL}/tracks",
                headers={
                    "x-api-key": API_KEY
                },
                timeout=60,
            )

            r.raise_for_status()

            data = r.json()

            self.tracks = data.get(
                "tracks",
                []
            )

            print("========== TRACKS RECIBIDOS ==========")
            print(self.tracks)
            print("TOTAL DE TEMAS:", len(self.tracks))
            print("======================================")

            banda = data.get(
                "banda",
                "RIA rock"
            )

            disco = data.get(
                "disco",
                "8´lineas"
            )

            descripcion = data.get(
                "descripcion",
                ""
            )

            self.set_ui_disco(
                banda,
                disco,
                descripcion
            )

        except Exception as e:

            print("ERROR CARGANDO TRACKLIST:")
            print(e)

            self.set_status(
                f"No se pudo conectar al servidor: {e}"
            )


    # ----------------------------------------------------------------
    # ACTUALIZAR INTERFAZ
    # ----------------------------------------------------------------

    @mainthread
    def set_ui_disco(
        self,
        banda,
        disco,
        descripcion
    ):

        root = self.player_screen.ids

        self.banda = banda
        self.disco = disco
        self.descripcion = descripcion

        root.banda_label.text = banda

        root.disco_label.text = disco

        if "descripcion_label" in root:
            root.descripcion_label.text = descripcion

        # Limpiar lista
        root.tracklist_box.clear_widgets()

        # Crear lista de temas
        for t in self.tracks:

            item = TrackItem()

            item.titulo = t.get(
                "titulo",
                "Tema sin nombre"
            )

            item.track_id = t.get(
                "id",
                ""
            )

            item.ids.track_btn.bind(
                on_release=lambda btn,
                tid=item.track_id:
                self.play_track(tid)
            )

            root.tracklist_box.add_widget(
                item
            )

        self.set_status(
            "Elegí un tema para reproducir"
        )

        # Cargar carátula
        self.cargar_caratula()


    # ----------------------------------------------------------------
    # CARATULA
    # ----------------------------------------------------------------

    def cargar_caratula(self):

        threading.Thread(
            target=self._descargar_caratula,
            daemon=True
        ).start()


    def _descargar_caratula(self):

        cache_path = os.path.join(
            self.cache_dir,
            "caratula.jpg"
        )

        if not os.path.exists(cache_path):

            try:

                print("Descargando carátula...")

                r = requests.get(
                    f"{SERVER_URL}/caratula",
                    headers={
                        "x-api-key": API_KEY
                    },
                    timeout=60,
                )

                r.raise_for_status()

                with open(
                    cache_path,
                    "wb"
                ) as f:

                    f.write(
                        r.content
                    )

                print("Carátula descargada.")

            except Exception as e:

                print("Error descargando carátula:")
                print(e)

                return

        if os.path.exists(cache_path):

            self.set_caratula(
                cache_path
            )


    @mainthread
    def set_caratula(self, path):

        self.player_screen.ids.caratula_img.source = path


    # ----------------------------------------------------------------
    # ESTADO
    # ----------------------------------------------------------------

    @mainthread
    def set_status(self, texto):

        self.player_screen.ids.status_label.text = texto


    # ----------------------------------------------------------------
    # REPRODUCIR TEMA
    # ----------------------------------------------------------------

    def play_track(self, track_id):

        if not track_id:
            return

        print("Solicitando tema:", track_id)

        cache_path = os.path.join(
            self.cache_dir,
            f"{track_id}.mp3"
        )

        # Si ya está descargado
        if os.path.exists(cache_path):

            print("Tema encontrado en cache.")

            self._reproducir_desde_cache(
                track_id,
                cache_path
            )

            return

        # Descargar
        print("Tema no encontrado en cache.")
        print("Descargando:", track_id)

        self.set_status(
            "Descargando tema..."
        )

        threading.Thread(
            target=self._descargar_y_reproducir,
            args=(
                track_id,
                cache_path
            ),
            daemon=True
        ).start()


    # ----------------------------------------------------------------
    # DESCARGAR MP3
    # ----------------------------------------------------------------

    def _descargar_y_reproducir(
        self,
        track_id,
        cache_path
    ):

        tmp_path = cache_path + ".part"

        try:

            r = requests.get(
                f"{SERVER_URL}/audio/{track_id}",
                headers={
                    "x-api-key": API_KEY
                },
                timeout=60,
                stream=True,
            )

            r.raise_for_status()

            with open(
                tmp_path,
                "wb"
            ) as f:

                for chunk in r.iter_content(
                    chunk_size=8192
                ):

                    if chunk:
                        f.write(chunk)

            os.replace(
                tmp_path,
                cache_path
            )

            print(
                "Descarga completada:",
                track_id
            )

            self._reproducir_desde_cache(
                track_id,
                cache_path
            )

        except Exception as e:

            print("ERROR DESCARGANDO MP3:")
            print(e)

            if os.path.exists(tmp_path):

                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            self.set_status(
                f"Error al descargar: {e}"
            )


    # ----------------------------------------------------------------
    # REPRODUCCION
    # ----------------------------------------------------------------

    @mainthread
    def _reproducir_desde_cache(
        self,
        track_id,
        cache_path
    ):

        # Detener tema anterior
        if self.sound:

            self.manual_stop = True

            try:
                self.sound.stop()
            except Exception:
                pass

            try:
                self.sound.unload()
            except Exception:
                pass

            self.sound = None

        # Cargar nuevo tema
        print("Cargando audio:", cache_path)

        self.sound = SoundLoader.load(
            cache_path
        )

        if not self.sound:

            print(
                "ERROR: SoundLoader no pudo cargar:",
                cache_path
            )

            self.set_status(
                "No se pudo reproducir el archivo"
            )

            self.is_playing = False

            return

        self.current_track_id = track_id

        self.is_playing = True

        self.manual_stop = False

        # Buscar título
        titulo = next(
            (
                t.get("titulo", track_id)
                for t in self.tracks
                if t.get("id") == track_id
            ),
            track_id
        )

        self.set_status(
            f"Reproduciendo: {titulo}"
        )

        print(
            "Reproduciendo:",
            titulo
        )

        self.sound.bind(
            on_stop=self._audio_stop
        )

        self.sound.play()


    # ----------------------------------------------------------------
    # EVENTO STOP DEL AUDIO
    # ----------------------------------------------------------------

    def _audio_stop(self, *args):

        # Si el stop fue provocado por nosotros,
        # no significa que el tema haya terminado.
        if self.manual_stop:
            self.manual_stop = False
            return

        self.on_track_finished()


    # ----------------------------------------------------------------
    # PLAY / PAUSA
    # ----------------------------------------------------------------

    def toggle_play_pause(self):

        if not self.sound:

            if self.tracks:

                self.play_track(
                    self.tracks[0].get("id")
                )

            return

        # ------------------------------------------------------------
        # PAUSAR
        # ------------------------------------------------------------

        if self.is_playing:

            try:

                self.manual_stop = True

                self.sound.stop()

                self.is_playing = False

                self.set_status(
                    "Reproducción detenida"
                )

            except Exception as e:

                self.set_status(
                    f"Error al detener: {e}"
                )

            return

        # ------------------------------------------------------------
        # VOLVER A REPRODUCIR
        # ------------------------------------------------------------

        try:

            self.manual_stop = False

            self.sound.play()

            self.is_playing = True

            titulo = next(
                (
                    t.get(
                        "titulo",
                        self.current_track_id
                    )
                    for t in self.tracks
                    if t.get("id")
                    == self.current_track_id
                ),
                self.current_track_id
            )

            self.set_status(
                f"Reproduciendo: {titulo}"
            )

        except Exception as e:

            self.set_status(
                f"Error de reproducción: {e}"
            )


    # ----------------------------------------------------------------
    # SIGUIENTE TEMA
    # ----------------------------------------------------------------

    def next_track(self):

        ids = [
            t.get("id")
            for t in self.tracks
            if t.get("id")
        ]

        if not ids:
            return

        if self.current_track_id in ids:

            i = ids.index(
                self.current_track_id
            )

        else:

            i = -1

        siguiente = ids[
            (i + 1) % len(ids)
        ]

        print(
            "Siguiente tema:",
            siguiente
        )

        self.play_track(
            siguiente
        )


    # ----------------------------------------------------------------
    # TEMA ANTERIOR
    # ----------------------------------------------------------------

    def prev_track(self):

        ids = [
            t.get("id")
            for t in self.tracks
            if t.get("id")
        ]

        if not ids:
            return

        if self.current_track_id in ids:

            i = ids.index(
                self.current_track_id
            )

        else:

            i = 0

        anterior = ids[
            (i - 1) % len(ids)
        ]

        print(
            "Tema anterior:",
            anterior
        )

        self.play_track(
            anterior
        )


    # ----------------------------------------------------------------
    # FINALIZACION DEL TEMA
    # ----------------------------------------------------------------

    def on_track_finished(self):

        self.is_playing = False

        self.set_status(
            "Tema finalizado. Elegí otro tema."
        )

        print(
            "Tema finalizado:",
            self.current_track_id
        )


# --------------------------------------------------------------------
# EJECUTAR APLICACION
# --------------------------------------------------------------------

if __name__ == "__main__":

    CDDigitalApp().run()

