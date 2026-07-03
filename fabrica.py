import os
import json
import random
import asyncio
import requests
import edge_tts
from google import genai
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# 🔑 LIBRERÍAS NUEVAS DE YOUTUBE
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 CLAVES SEGURAS DESDE GITHUB SECRETS
GEMINI_KEY = os.environ.get("AQ.Ab8RN6JVa8vZt7tGu8hNjVgxOri0n4vpDNaTriPV0_0zSdVJeQ")
PEXELS_KEY = os.environ.get("FAxCoyD8kp3eVyrPeQOQHSCjHkEYwswmKhPrSyTWAE65AS0yBeSFG37j")

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

    url = f"https://pexels.com{tema}&orientation=portrait&per_page=5"
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

# 🚀 FUNCIÓN MÁGICA PARA SUBIR A YOUTUBE SHORTS
def subir_a_youtube(archivo_video, titulo, descripcion):
    print("\n>>> [YOUTUBE API] Iniciando proceso de subida...")
    try:
        # Reconstruimos las credenciales desde el secreto de GitHub
        secrets_env = os.environ.get("CLIENT_SECRETS_JSON")
        if not secrets_env:
            print("[ERROR YOUTUBE] No se encontraron las credenciales CLIENT_SECRETS_JSON.")
            return

        secrets_data = json.loads(secrets_env)
        
        # Simulación de tokens para entorno automatizado
        # NOTA: YouTube requiere un flujo OAuth inicial. Si salta error de token, 
        # configuraremos un token de refresco persistente.
        print("[YOUTUBE API] Autenticando con los canales de Google...")
        
        # Estructura básica de conexión por API
        # (Usa un token de acceso rápido simulado para el despliegue inicial)
        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN", "dummy_token"),
            token_uri="https://googleapis.com",
            client_id=secrets_data.get("installed", {}).get("client_id"),
            client_secret=secrets_data.get("installed", {}).get("client_secret")
        )
        
        youtube = build("youtube", "v3", credentials=creds)
        
        body = {
            "snippet": {
                "title": titulo[:100],
                "description": descripcion,
                "tags": ["shorts", "datoscuriosos", "ia"],
                "categoryId": "27" # Educación / Ciencia
            },
            "status": {
                "privacyStatus": "public", # Se lanza directo al público
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(archivo_video, chunksize=-1, resumable=True, mimetype="video/mp4")
        
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        print("[YOUTUBE API] Subiendo archivo MP4 a la plataforma...")
        response = request.execute()
        print(f"[YOUTUBE API] ¡ÉXITO TOTAL! Video subido. ID: {response.get('id')}")
        
    except Exception as e:
        print(f"[AVISO YOUTUBE] Error en subida automática: {e}")
        print("[CONSEJO] Si dice 'invalid_grant', necesitamos generar el Refresh Token manual la primera vez.")

async def main():
    print(">>> [YouMega2] Iniciando generador 100% Autónomo...")
    
    try:
        tema, texto_guion = await obtener_guion_ia()
    except Exception:
        print("\n[AVISO] La IA de Google está al límite. Activando plan de respaldo...")
        tema = "el espacio exterior"
        texto_guion = "el espacio exterior esconde misterios increibles como estrellas que giran miles de veces por segundo en absoluto silencio"
        
    try:
        print(f"[GUION DETERMINADO]: '{texto_guion}'")
        
        archivo_audio = "audio_temporal.mp3"
        await generar_voz(texto_guion, archivo_audio)
        
        ruta_fondo = descargar_video_fondo(tema)
        
        archivo_salida = f"short_{tema.replace(' ', '_')}.mp4"
        armar_video_final(archivo_audio, ruta_fondo, archivo_salida, texto_guion)
        
        # 🎬 SUBIDA AUTOMÁTICA
        titulo_short = f"¿Sabías esto sobre {tema}? 😱 #shorts #curiosidades"
        subir_a_youtube(archivo_salida, titulo_short, texto_guion)
        
        if os.path.exists(archivo_audio):
            os.remove(archivo_audio)
            
    except Exception as e:
        print(f"[ERROR EN PROCESO]: {e}")

if __name__ == "__main__":
    asyncio.run(main())
