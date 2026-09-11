import os
import shutil
import urllib.parse
import webbrowser

# --- CONFIGURACIÓN DE TU SERVIDOR ---
# Reemplaza con la URL real de tu servicio desplegado en Render:
SERVER_URL = "https://tu-app-en-render.onrender.com"
API_KEY = "cambiar-esta-clave-123"

# Ruta de la carpeta de caché local en Windows
CACHE_DIR = os.path.join(os.getenv("APPDATA"), "cddigital", ".cd_digital_cache")


def limpiar_cache_pc():
    """Elimina la caché de la PC para forzar la descarga del audio correcto."""
    if os.path.exists(CACHE_DIR):
        try:
            shutil.rmtree(CACHE_DIR)
            print("✅ Caché local eliminada correctamente.")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar la caché: {e}")
    else:
        print("ℹ️ La carpeta de caché ya está limpia.")


def obtener_links_tracks():
    """Genera las URLs directas para cada pista enviando la API Key."""
    tracks = [
        {"id": "track01", "titulo": "Volvimos a adjuntar"},
        {"id": "track02", "titulo": "Unidad"},
        {"id": "track03", "titulo": "Cómo"},
        {"id": "track04", "titulo": "Justo"},
        {"id": "track05", "titulo": "Cualidad"},
        {"id": "track06", "titulo": "Vestidos de negro"},
        {"id": "track07", "titulo": "Amar es solo un sueño 2"},
        {"id": "track08", "titulo": "Olla popular"}
    ]

    print("\n--- ENLACES DIRECTOS A LOS TEMAS ---")
    links = {}
    for track in tracks:
        # Pasa la API Key como parámetro en la URL si tu cliente/navegador lo soporta
        api_key_encoded = urllib.parse.quote(API_KEY)
        link = f"{SERVER_URL}/audio/{track['id']}?x_api_key={api_key_encoded}"
        links[track["id"]] = link
        print(f"🎵 {track['titulo']}: {link}")
    
    return links


if __name__ == "__main__":
    # 1. Borra la caché vieja
    limpiar_cache_pc()

    # 2. Obtiene los enlaces
    links = obtener_links_tracks()

    # 3. Abre el Track 1 ("Volvimos a adjuntar") directamente en el navegador por defecto
    print("\nAbriendo el Tema 01 en el navegador...")
    webbrowser.open(links["track01"])