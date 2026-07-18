import os
import json
import random
import asyncio
import requests
import edge_tts
import google.genai as genai
from moviepy import (
    VideoFileClip, AudioFileClip, AudioClip, CompositeAudioClip,
    concatenate_videoclips
)
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# 🔑 LIBRERÍAS DE YOUTUBE (API OFICIAL)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 SECRETOS DE GITHUB
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

# Resolución estándar para Shorts (vertical)
ANCHO_ESTANDAR = 1080
ALTO_ESTANDAR = 1920

# Archivo con la música de fondo libre de derechos (subila a tu repo con este nombre,
# o cambiá el nombre acá por el que le hayas puesto)
ARCHIVO_MUSICA_FONDO = "musica_fondo.mp3"

# 📋 PLANTEL DE 26 JUGADORES - MUNDIAL 2026 (orden: arqueros, defensores, mediocampistas, delanteros)
PLANTEL = [
    {"numero": 23, "nombre": "Emiliano Martínez", "posicion": "Arquero"},
    {"numero": 12, "nombre": "Gerónimo Rulli", "posicion": "Arquero"},
    {"numero": 1, "nombre": "Juan Musso", "posicion": "Arquero"},
    {"numero": 26, "nombre": "Nahuel Molina", "posicion": "Defensor"},
    {"numero": 4, "nombre": "Gonzalo Montiel", "posicion": "Defensor"},
    {"numero": 13, "nombre": "Cristian Romero", "posicion": "Defensor"},
    {"numero": 6, "nombre": "Marcos Senesi", "posicion": "Defensor"},
    {"numero": 19, "nombre": "Nicolás Otamendi", "posicion": "Defensor"},
    {"numero": 25, "nombre": "Lisandro Martínez", "posicion": "Defensor"},
    {"numero": 3, "nombre": "Nicolás Tagliafico", "posicion": "Defensor"},
    {"numero": 24, "nombre": "Facundo Medina", "posicion": "Defensor"},
    {"numero": 5, "nombre": "Leandro Paredes", "posicion": "Mediocampista"},
    {"numero": 20, "nombre": "Alexis Mac Allister", "posicion": "Mediocampista"},
    {"numero": 7, "nombre": "Rodrigo De Paul", "posicion": "Mediocampista"},
    {"numero": 21, "nombre": "Giovani Lo Celso", "posicion": "Mediocampista"},
    {"numero": 14, "nombre": "Exequiel Palacios", "posicion": "Mediocampista"},
    {"numero": 24, "nombre": "Enzo Fernández", "posicion": "Mediocampista"},
    {"numero": 17, "nombre": "Valentín Barco", "posicion": "Mediocampista"},
    {"numero": 10, "nombre": "Lionel Messi", "posicion": "Delantero"},
    {"numero": 9, "nombre": "Julián Álvarez", "posicion": "Delantero"},
    {"numero": 22, "nombre": "Lautaro Martínez", "posicion": "Delantero"},
    {"numero": 16, "nombre": "Thiago Almada", "posicion": "Delantero"},
    {"numero": 8, "nombre": "Nicolás Paz", "posicion": "Delantero"},
    {"numero": 11, "nombre": "Nicolás González", "posicion": "Delantero"},
    {"numero": 18, "nombre": "Giuliano Simeone", "posicion": "Delantero"},
    {"numero": 15, "nombre": "José Manuel López", "posicion": "Delantero"},
]

ARCHIVO_PROGRESO = "progreso_figuritas.json"


def leer_progreso():
    """Lee cuál es el próximo jugador en la lista. Si no existe el archivo, arranca desde el primero."""
    if os.path.exists(ARCHIVO_PROGRESO):
        with open(ARCHIVO_PROGRESO, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return datos.get("siguiente_indice", 0)
    return 0


def guardar_progreso(indice_siguiente):
    """Guarda cuál es el próximo jugador a cubrir la próxima vez que corra el bot."""
    # Si ya recorrimos todo el plantel, volvemos a empezar desde el principio
    if indice_siguiente >= len(PLANTEL):
        indice_siguiente = 0
    with open(ARCHIVO_PROGRESO, "w", encoding="utf-8") as f:
        json.dump({"siguiente_indice": indice_siguiente}, f, ensure_ascii=False, indent=2)


async def generar_voz(texto, archivo_salida):
    try:
        VOICE = "es-AR-TomasNeural"  # voz en español argentino
        communicate = edge_tts.Communicate(texto, VOICE)
        await communicate.save(archivo_salida)
    except Exception as e:
        print(f"[AVISO] Voz principal falló. Activando gTTS de respaldo... ({e})")
        from gtts import gTTS
        tts = gTTS(text=texto, lang='es', tld='com.ar')
        tts.save(archivo_salida)


def obtener_dato_jugador_ia(jugador):
    """Le pide a Gemini un dato REAL y verificado sobre la vida/carrera del jugador.
    Se le exige explícitamente que no invente nada."""
    print(f"\n[IA] Pidiéndole a Gemini datos reales de {jugador['nombre']}...")

    prompt = (
        f"Necesito un guion corto y factual para un Short de YouTube sobre el jugador de fútbol "
        f"{jugador['nombre']}, que juega de {jugador['posicion']} en la Selección Argentina "
        f"para el Mundial 2026, con la camiseta número {jugador['numero']}. "
        f"Escribí de 3 a 4 oraciones (entre 45 y 65 palabras en total) con datos REALES y VERIFICABLES "
        f"sobre su carrera: club donde surgió, hitos importantes, o su rol en la Selección. "
        f"IMPORTANTE: NO inventes datos, fechas, ni anécdotas que no estés seguro que sean ciertas. "
        f"Si no tenés información confiable sobre algún dato específico, quedate con generalidades "
        f"conocidas de su carrera en vez de inventar detalles. "
        f"No uses acentos ni la letra ñ (reemplazala por n). "
        f"Devolvé UNICAMENTE un JSON limpio, sin bloques de markdown, con esta estructura:\n"
        f'{{"narracion": "el texto del guion aca"}}'
    )

    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    texto_json = response.text.strip().replace("```json", "").replace("```", "")

    inicio = texto_json.find("{")
    fin = texto_json.rfind("}")
    if inicio != -1 and fin != -1:
        texto_json = texto_json[inicio:fin + 1]

    datos = json.loads(texto_json)
    return datos["narracion"]


def descargar_video_generico_futbol():
    """Descarga un video GENÉRICO de fútbol (pelota, estadio, cancha) SIN caras de jugadores reales,
    para evitar mostrar por error a una persona distinta a la que se está nombrando."""
    if not PEXELS_API_KEY:
        print("[ERROR] Falta configurar PEXELS_API_KEY.")
        return None

    os.makedirs("clips_temporales", exist_ok=True)
    ruta_guardado = os.path.join("clips_temporales", "video_fondo.mp4")

    # Términos 100% genéricos y seguros: nada de nombres, nada que muestre caras reconocibles
    opciones_seguras = [
        "soccer ball close up slow motion",
        "stadium lights night empty",
        "football net goal close up",
        "stadium crowd cheering from behind",
        "soccer field grass close up",
        "football stadium aerial view",
    ]
    palabras_clave = random.choice(opciones_seguras)

    url = f"https://api.pexels.com/videos/search?query={palabras_clave}&orientation=portrait&per_page=5"
    headers = {"Authorization": PEXELS_API_KEY}

    try:
        response = requests.get(url, headers=headers).json()
        videos = response.get("videos", [])
        if not videos:
            # Si no hay resultados en vertical, probamos en horizontal (lo recortamos después igual)
            url = f"https://api.pexels.com/videos/search?query={palabras_clave}&per_page=5"
            response = requests.get(url, headers=headers).json()
            videos = response.get("videos", [])

        if videos:
            video_elegido = random.choice(videos)
            video_files = video_elegido.get("video_files", [])

            candidatos_hd = [
                v for v in video_files
                if v.get("quality") == "hd" and v.get("width", 0) >= 720
            ]
            if candidatos_hd:
                mejor = max(candidatos_hd, key=lambda v: v.get("width", 0))
            else:
                mejor = max(video_files, key=lambda v: v.get("width", 0))

            download_url = mejor.get("link")
            if download_url:
                video_data = requests.get(download_url).content
                with open(ruta_guardado, "wb") as f:
                    f.write(video_data)
                return ruta_guardado
    except Exception as e:
        print(f"[ERROR DESCARGA VIDEO FONDO]: {e}")
    return None


def armar_short_figurita(jugador, ruta_video_fondo, archivo_audio, texto_narracion):
    """Arma el video final: fondo genérico + tarjeta de 'figurita' (número + nombre) + narración + música."""
    video_clip = VideoFileClip(ruta_video_fondo)
    audio_voz = AudioFileClip(archivo_audio)
    duracion = audio_voz.duration

    if video_clip.duration < duracion:
        repeticiones = int(duracion / video_clip.duration) + 1
        video_clip = concatenate_videoclips([video_clip] * repeticiones)
    video_clip = video_clip.subclipped(0, duracion)

    # Forzamos resolución estándar vertical (evita el efecto mosaico si Pexels da otro tamaño)
    video_clip = video_clip.resized(height=ALTO_ESTANDAR)
    if video_clip.w < ANCHO_ESTANDAR:
        video_clip = video_clip.resized(width=ANCHO_ESTANDAR)
    video_clip = video_clip.cropped(
        x_center=video_clip.w / 2,
        y_center=video_clip.h / 2,
        width=ANCHO_ESTANDAR,
        height=ALTO_ESTANDAR
    )

    # 🎴 La "tarjeta de figurita": número grande + nombre, arriba de la pantalla
    tamano_fuente_numero = int(ALTO_ESTANDAR * 0.06)
    tamano_fuente_nombre = int(ALTO_ESTANDAR * 0.035)

    texto_numero = (TextClip(
        text=f"N° {jugador['numero']}",
        font_size=tamano_fuente_numero,
        color='gold',
        stroke_color='black',
        stroke_width=4,
        size=(int(ANCHO_ESTANDAR * 0.9), int(ALTO_ESTANDAR * 0.12)),
        method='caption',
        text_align='center'
     ).with_start(0).with_duration(duracion).with_position(('center', int(ALTO_ESTANDAR * 0.08))))

    texto_nombre = (TextClip(
        text=jugador['nombre'].upper(),
        font_size=tamano_fuente_nombre,
        color='white',
        stroke_color='black',
        stroke_width=3,
        size=(int(ANCHO_ESTANDAR * 0.9), int(ALTO_ESTANDAR * 0.08)),
        method='caption',
        text_align='center'
     ).with_start(0).with_duration(duracion).with_position(('center', int(ALTO_ESTANDAR * 0.20))))

    # Subtítulo de la narración, abajo
    tamano_fuente_sub = int(ALTO_ESTANDAR * 0.018)
    subtitulo = (TextClip(
        text=texto_narracion.upper(),
        font_size=tamano_fuente_sub,
        color='white',
        stroke_color='black',
        stroke_width=2,
        size=(int(ANCHO_ESTANDAR * 0.85), int(ALTO_ESTANDAR * 0.25)),
        method='caption',
        text_align='center'
     ).with_start(0).with_duration(duracion).with_position(('center', 'bottom')))

    # 🎵 Música de fondo a bajo volumen (si el archivo existe)
    audio_final = audio_voz
    if os.path.exists(ARCHIVO_MUSICA_FONDO):
        musica = AudioFileClip(ARCHIVO_MUSICA_FONDO).with_volume_scaled(0.15)
        if musica.duration < duracion:
            repeticiones_audio = int(duracion / musica.duration) + 1
            musica = concatenate_videoclips([musica] * repeticiones_audio) if False else musica
        musica = musica.subclipped(0, min(musica.duration, duracion))
        audio_final = CompositeAudioClip([musica, audio_voz])
    else:
        print(f"[AVISO] No se encontró '{ARCHIVO_MUSICA_FONDO}' — el video va a salir sin música de fondo.")

    video_final = CompositeVideoClip([video_clip, texto_numero, texto_nombre, subtitulo]).with_audio(audio_final)

    ruta_salida = "short_figurita_final.mp4"
    video_final.write_videofile(ruta_salida, codec="libx264", audio_codec="aac", fps=24, logger=None)

    video_clip.close()
    audio_voz.close()
    video_final.close()
    return ruta_salida


def subir_a_youtube(archivo_video, titulo, descripcion):
    print("\n>>> [YOUTUBE API] Iniciando proceso de subida...")
    try:
        secrets_env = os.environ.get("CLIENT_SECRETS_JSON")
        if not secrets_env:
            return

        secrets_data = json.loads(secrets_env, strict=False)
        datos_credenciales = secrets_data.get("installed") or secrets_data.get("web") or {}

        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=datos_credenciales.get("client_id"),
            client_secret=datos_credenciales.get("client_secret")
        )

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": titulo[:100],
                "description": descripcion,
                "tags": ["seleccionargentina", "mundial2026", "figuritas", "futbol"],
                "categoryId": "17"  # Deportes
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(archivo_video, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        print(f"[YOUTUBE API] Subiendo figurita...")
        response = request.execute()
        print(f"[SISTEMA] ¡Figurita subida con éxito! ID: {response.get('id')}")
    except Exception as e:
        print(f"[ERROR YOUTUBE API]: {e}")


async def main():
    os.makedirs("clips_temporales", exist_ok=True)

    indice = leer_progreso()
    jugador = PLANTEL[indice]
    print(f"\n=== FIGURITA #{indice + 1}/{len(PLANTEL)}: {jugador['nombre']} (N° {jugador['numero']}) ===")

    try:
        narracion = obtener_dato_jugador_ia(jugador)
    except Exception as e:
        print(f"[ERROR AL GENERAR GUION]: {e}")
        return

    print(f"[GUION] {narracion}")

    audio_temp = os.path.join("clips_temporales", "voz.mp3")
    await generar_voz(narracion, audio_temp)

    video_fondo = descargar_video_generico_futbol()
    if not video_fondo:
        print("[ERROR] No se pudo descargar el video de fondo. Abortando esta corrida.")
        return

    ruta_final = armar_short_figurita(jugador, video_fondo, audio_temp, narracion)

    titulo = f"Figurita N° {jugador['numero']} — {jugador['nombre']} | Selección Argentina 2026 ⚽"
    descripcion = (
        f"{jugador['nombre']} — {jugador['posicion']} — N° {jugador['numero']}\n\n"
        f"{narracion}\n\n"
        f"#SeleccionArgentina #Mundial2026 #Figuritas"
    )
    subir_a_youtube(ruta_final, titulo, descripcion)

    # Guardamos que el próximo jugador a cubrir es el siguiente de la lista
    guardar_progreso(indice + 1)
    print("[SISTEMA] Listo. La próxima corrida seguirá con el siguiente jugador del plantel.")


if __name__ == "__main__":
    asyncio.run(main())
