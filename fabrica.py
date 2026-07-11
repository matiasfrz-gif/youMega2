import os
import json
import random
import asyncio
import requests
import edge_tts
from google import genai
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

# 🔑 LIBRERÍAS DE YOUTUBE
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 CLAVES SEGURAS DESDE LAS VARIABLES DE ENTORNO
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

async def generar_voz(texto, archivo_salida):
    try:
        VOICE = "es-MX-AlvaroNeural"
        communicate = edge_tts.Communicate(texto, VOICE)
        await communicate.save(archivo_salida)
        print(f"[AUDIO] Voz principal creada con éxito.")
    except Exception as e:
        print(f"[AVISO] Voz principal falló. Activando respaldo de Google...")
        from gtts import gTTS
        tts = gTTS(text=texto, lang='es', tld='com.mx')
        tts.save(archivo_salida)
        print(f"[AUDIO] Voz de respaldo creada con éxito.")

async def obtener_guion_ia():
    temas = ["las piramides de Egipto", "el espacio exterior", "el Imperio Romano", "misterios del oceano"]
    tema_elegido = random.choice(temas)

    print(f"\n[IA] Pidiéndole a Gemini un dato corto sobre: {tema_elegido}...")

    prompt = f"Escribi un dato curioso e impactante sobre {tema_elegido}. Debe ser un texto corto, fluido y atractivo para un video de YouTube Short. Maximo 35 palabras. No uses vinetas, titulos, hashtags, comillas, signos de preguntas ni exclamaciones. Solo texto corrido limpio."

    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    texto_original = response.text.strip()

    texto_seguro = texto_original.encode('utf-8', errors='ignore').decode('utf-8')

    texto_limpio = texto_seguro.lower()
    remplazos_letras = {
        "ña": "nia", "ñe": "nie", "ñi": "nii", "ño": "nio", "ñu": "niu",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "ni"
    }
    for original, nuevo in remplazos_letras.items():
        texto_limpio = texto_limpio.replace(original, nuevo)

    caracteres_raros = ["'", '"', "«", "»", "“", "”", "¿", "?", "¡", "!", ",", ".", ";", ":", "-", "_"]
    for caracter in caracteres_raros:
        texto_limpio = texto_limpio.replace(caracter, "")

    return tema_elegido, texto_limpio

def descargar_video_fondo(tema):
    print(f"[VIDEO IA] Buscando un fondo ideal para '{tema}' en internet...")

    if not PEXELS_KEY:
        print("[ERROR] Falta configurar la variable PEXELS_API_KEY.")
        return None

    os.makedirs("fondos", exist_ok=True)
    ruta_guardado = os.path.join("fondos", f"fondo_{tema.replace(' ', '_')}.mp4")

    if os.path.exists(ruta_guardado):
        return ruta_guardado

    url = f"https://api.pexels.com/videos/search?query={tema}&orientation=portrait&per_page=5"
    headers = {"Authorization": PEXELS_KEY}

    try:
        response = requests.get(url, headers=headers).json()
        videos = response.get("videos", [])

        if videos:
            video_elegido = random.choice(videos)
            video_files = video_elegido.get("video_files", [])

            download_url = None
            if isinstance(video_files, list) and len(video_files) > 0:
                download_url = video_files[0].get("link")
            elif isinstance(video_files, dict):
                download_url = video_files.get("link")

            if download_url:
                print("[VIDEO IA] Descargando video de stock encontrado...")
                video_data = requests.get(download_url).content
                with open(ruta_guardado, "wb") as f:
                    f.write(video_data)
                return ruta_guardado
            else:
                print("[VIDEO IA] No se encontro un link de descarga valido.")
                return None
        else:
            print("[VIDEO IA] No se encontraron videos especificos.")
            return None
    except Exception as e:
        print(f"[ERROR DESCARGA]: {e}")
        return None

def armar_video_final(archivo_audio, ruta_fondo, archivo_video_salida, texto_guion):
    print("\n>>> [MOVIEPY] Iniciando el montaje final con subtítulos...")

    if not ruta_fondo or not os.path.exists(ruta_fondo):
        print("[ERROR VIDEO] No se pudo obtener un video de fondo válido.")
        return

    video_clip = VideoFileClip(ruta_fondo)
    audio_clip = AudioFileClip(archivo_audio)

    duracion = audio_clip.duration

    # Si el video de fondo es más corto que el audio, lo repetimos hasta que alcance
    if video_clip.duration < duracion:
        print(f"[MOVIEPY] Video corto ({video_clip.duration:.1f}s), extendiendo para cubrir {duracion:.1f}s...")
        repeticiones = int(duracion / video_clip.duration) + 1
        video_extendido = concatenate_videoclips([video_clip] * repeticiones)
        video_recortado = video_extendido.subclipped(0, duracion)
    else:
        video_recortado = video_clip.subclipped(0, duracion)

    print("[MOVIEPY] Generando subtítulos en pantalla...")
    palabras = texto_guion.split()
    total_palabras = len(palabras)

    tiempo_por_palabra = duracion / total_palabras
    clips_de_texto = []

    grupo = []
    for i, palabra in enumerate(palabras):
        grupo.append(palabra)
        if len(grupo) == 3 or i == total_palabras - 1:
            texto_pantalla = " ".join(grupo).upper()

            inicio_texto = (i - len(grupo) + 1) * tiempo_por_palabra
            fin_texto = (i + 1) * tiempo_por_palabra

            subtitulo = (TextClip(
                            text=texto_pantalla,
                            font_size=50,
                            color='yellow',
                            stroke_color='black',
                            stroke_width=3
                         )
                         .with_start(inicio_texto)
                         .with_duration(fin_texto - inicio_texto)
                         .with_position(('center', 'center')))

            clips_de_texto.append(subtitulo)
            grupo = []

    video_con_subtitulos = CompositeVideoClip([video_recortado] + clips_de_texto)
    video_final = video_con_subtitulos.with_audio(audio_clip)

    print(f"[MOVIEPY] Exportando Short con subtítulos...")
    video_final.write_videofile(
        archivo_video_salida,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        logger=None
    )

    video_clip.close()
    audio_clip.close()
    video_final.close()
    print(f"[SISTEMA] ¡Video creado con éxito!: {archivo_video_salida}")

def subir_a_youtube(archivo_video, titulo, descripcion):
    print("\n>>> [YOUTUBE API] Iniciando proceso de subida...")
    try:
        secrets_env = os.environ.get("CLIENT_SECRETS_JSON")
        if not secrets_env:
            print("[ERROR YOUTUBE] No se encontraron las credenciales CLIENT_SECRETS_JSON.")
            return

        secrets_data = json.loads(secrets_env)
        print("[YOUTUBE API] Autenticando con los canales de Google...")

        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=secrets_data.get("installed", {}).get("client_id"),
            client_secret=secrets_data.get("installed", {}).get("client_secret")
        )

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": titulo[:100],
                "description": descripcion,
                "tags": ["shorts", "datoscuriosos", "ia"],
                "categoryId": "27"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(archivo_video, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        print("[YOUTUBE API] Subiendo archivo...")
        response = request.execute()
        print(f"[YOUTUBE API] ¡Video subido con éxito! ID del video: {response.get('id')}")

    except Exception as e:
        print(f"[ERROR YOUTUBE API]: {e}")

# 🚀 FUNCIÓN PRINCIPAL QUE EJECUTA TODO EL PROCESO
async def main():
    tema, guion = await obtener_guion_ia()
    archivo_audio = "voz_temporal.mp3"
    archivo_video_final = "short_final.mp4"

    await generar_voz(guion, archivo_audio)
    ruta_fondo = descargar_video_fondo(tema)

    if ruta_fondo:
        armar_video_final(archivo_audio, ruta_fondo, archivo_video_final, guion)
        subir_a_youtube(archivo_video_final, f"Dato Curioso sobre {tema.capitalize()} #shorts", guion)
    else:
        print("[SISTEMA] No se pudo completar el proceso porque falló la descarga del fondo.")

if __name__ == "__main__":
    asyncio.run(main())
