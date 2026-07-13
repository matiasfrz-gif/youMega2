import os
import json
import random
import asyncio
import requests
import google.genai as genai
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# 🔑 LIBRERÍAS DE YOUTUBE (API OFICIAL)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 RECOLECCIÓN DE TUS SECRETOS ACTUALES DE GITHUB
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Inicializamos Gemini con tu llave actual
client = genai.Client(api_key=GEMINI_KEY)

async def generar_voz_escena(texto, archivo_salida):
    try:
        VOICE = "es-MX-JorgeNeural" 
        communicate = edge_tts.Communicate(texto, VOICE)
        await communicate.save(archivo_salida)
    except Exception as e:
        print(f"[AVISO] Voz principal falló en escena. Activando gTTS de respaldo...")
        from gtts import gTTS
        tts = gTTS(text=texto, lang='es', tld='com.mx')
        tts.save(archivo_salida)

async def obtener_guion_zombis_ia():
    # El archivo de memoria para que el bot nunca olvide el capítulo anterior
    archivo_memoria = "historial_serie_rene.json"
    resumen_anterior = "Rene Enriquez acaba de despertar desorientado en medio del brote zombie."

    # Si el archivo existe en el repositorio, lee cómo terminó el capítulo de ayer
    if os.path.exists(archivo_memoria):
        try:
            with open(archivo_memoria, "r") as f:
                datos_memoria = json.load(f)
                resumen_anterior = datos_memoria.get("ultimo_resumen", resumen_anterior)
            print(f"[MEMORIA] ¡Contexto recuperado! Capitulo anterior: '{resumen_anterior}'")
        except Exception as e:
            print("[AVISO MEMORIA] Usando inicio por defecto.")

    print(f"\n[IA] Pidiéndole a Gemini el siguiente capítulo de la serie de Rene Enriquez...")

    prompt = (
        f"Eres el escritor principal de una serie cinematografica de terror y supervivencia zombie. "
        f"El protagonista absoluto es un hombre llamado Rene Enriquez. "
        f"En el capitulo anterior ocurrio exactamente esto: '{resumen_anterior}'. "
        f"Escribe el CAPITULO SIGUIENTE de la serie continuando la narrativa de forma fluida, tensa y atrapante. "
        f"Divide este nuevo capitulo en exactamente 10 escenas consecutivas. "
        f"Devuelve el resultado UNICAMENTE en formato JSON limpio, sin bloques de codigo markdown (no uses ```json), "
        f"con la siguiente estructura exacta:\n"
        f"{{\n"
        f"  \"nuevo_resumen\": \"Un parrafo corto que sintetice como termina Rene en este nuevo episodio para guardarlo en la memoria.\",\n"
        f"  \"escenas\": [\n"
        f"    {{\"escena\": 1, \"narracion\": \"Texto que dira el locutor sin acentos ni enies.\", \"video_prompt\": \"Palabras clave fisicas en ingles\"}},\n"
        f"    ...\n"
        f"  ]\n"
        f"}}\n"
        f"REGLAS CRÍTICAS: No uses acentos ni letras enie en el campo de narracion. "
        f"El video_prompt debe contener unicamente descripciones visuales literales en ingles de lo que pasa (ejemplos: 'man running back view', 'dark hospital corridor'). No uses emociones."
    )

    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    texto_json = response.text.strip().replace("```json", "").replace("```", "")
    
    datos_guion = json.loads(texto_json)
    
    # Guardamos de forma automática el nuevo resumen para la próxima corrida
    try:
        with open(archivo_memoria, "w") as f:
            json.dump({"ultimo_resumen": datos_guion["nuevo_resumen"]}, f, indent=4)
    except Exception as e:
        print(f"[ERROR MEMORIA]: {e}")

    return datos_guion["escenas"]

def descargar_video_escena(prompt_video, num_escena, texto_narracion):
    if not PEXELS_API_KEY:
        print("[ERROR] Falta configurar PEXELS_API_KEY.")
        return None

    os.makedirs("clips_temporales", exist_ok=True)
    ruta_guardado = os.path.join("clips_temporales", f"video_{num_escena}.mp4")

    # 🚨 EL DOMADOR DE PEXELS DE LA SERIE: Filtramos palabras de acción real
    texto_min = texto_narracion.lower()
    
    if "corriendo" in texto_min or "corre" in texto_min or "escapa" in texto_min or "huye" in texto_min:
        palabras_clave = "person running away camera"
    elif "oscur" in texto_min or "noche" in texto_min or "sombra" in texto_min:
        palabras_clave = "dark abandoned corridor"
    elif "zombie" in texto_min or "monstruo" in texto_min or "horda" in texto_min or "infectado" in texto_min:
        palabras_clave = "scary monster cinematic"
    elif "cristal" in texto_min or "rompio" in texto_min or "ventana" in texto_min or "ruido" in texto_min:
        palabras_clave = "dark spooky laboratory"
    else:
        # Limpieza si la escena de René es más descriptiva
        prompt_limpio = prompt_video.replace(",", " ").replace(".", " ")
        palabras_clave = " ".join(prompt_limpio.split()[:3])

    print(f"[BOT] Escena {num_escena} -> Buscando en Pexels con filtro: '{palabras_clave}'")

    url = f"https://pexels.com{palabras_clave}&orientation=landscape&per_page=3"
    headers = {"Authorization": PEXELS_API_KEY}

    try:
        response = requests.get(url, headers=headers).json()
        videos = response.get("videos", [])
        if videos:
            video_elegido = random.choice(videos)
            video_files = video_elegido.get("video_files", [])
            
            download_url = None
            if isinstance(video_files, list) and len(video_files) > 0:
                download_url = video_files.get("link")
            elif isinstance(video_files, dict):
                download_url = video_files.get("link")

            if download_url:
                video_data = requests.get(download_url).content
                with open(ruta_guardado, "wb") as f:
                    f.write(video_data)
                return ruta_guardado
    except Exception as e:
        print(f"[ERROR DESCARGA ESCENA {num_escena}]: {e}")
    return None

def armar_bloque_escena(archivo_audio, ruta_fondo, texto_narracion, num_escena):
    video_clip = VideoFileClip(ruta_fondo)
    audio_clip = AudioFileClip(archivo_audio)
    duracion = audio_clip.duration

    if video_clip.duration < duracion:
        repeticiones = int(duracion / video_clip.duration) + 1
        video_extendido = concatenate_videoclips([video_clip] * repeticiones)
        video_recortado = video_extendido.subclipped(0, duracion)
    else:
        video_recortado = video_clip.subclipped(0, duracion)

    subtitulo = (TextClip(
        text=texto_narracion.upper(),
        font_size=28,
        color='white',
        stroke_color='black',
        stroke_width=3,
        size=(1100, 150),
        method='caption',
        text_align='center'
     )
     .with_start(0)
     .with_duration(duracion)
     .with_position(('center', 'bottom')))

    escena_montada = CompositeVideoClip([video_recortado, subtitulo]).with_audio(audio_clip)
    ruta_salida_bloque = os.path.join("clips_temporales", f"bloque_listo_{num_escena}.mp4")
    escena_montada.write_videofile(ruta_salida_bloque, codec="libx264", audio_codec="aac", fps=24, logger=None)
    
    video_clip.close()
    audio_clip.close()
    escena_montada.close()
    return ruta_salida_bloque

def subir_a_youtube(archivo_video, titulo, descripcion):
    print("\n>>> [YOUTUBE API] Iniciando proceso de subida...")
    try:
        secrets_env = os.environ.get("CLIENT_SECRETS_JSON")
        if not secrets_env: return

        secrets_data = json.loads(secrets_env, strict=False)
        datos_credenciales = secrets_data.get("installed") or secrets_data.get("web") or {}

        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("YOUTUBE_REFRESH_TOKEN"),
            token_uri="https://googleapis.com",
            client_id=datos_credenciales.get("client_id"),
            client_secret=datos_credenciales.get("client_secret")
        )

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": titulo[:100],
                "description": descripcion,
                "tags": ["rene_enriquez", "serie_terror", "zombies", "ia"],
                "categoryId": "24"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(archivo_video, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        print(f"[YOUTUBE API] Subiendo capitulo de la serie...")
        response = request.execute()
        print(f"[SISTEMA] ¡Video de René subido! ID: {response.get('id')}")
    except Exception as e:
        print(f"[ERROR YOUTUBE API]: {e}")

async def main():
    os.makedirs("clips_temporales", exist_ok=True)
    archivo_pelicula_final = "serie_rene_enriquez_capitulo.mp4"

    try:
        lista_escenas = await obtener_guion_zombis_ia()
    except Exception as e:
        print(f"[ERROR SINTAXIS JSON]: {e}")
        return

    bloques_renderizados = []

    for escena in lista_escenas:
        num = escena["escena"]
        print(f"\n--- TRABAJANDO EN ESCENA {num}/10 ---")
        audio_temp = os.path.join("clips_temporales", f"voz_{num}.mp3")
        
        await generar_voz_escena(escena["narracion"], audio_temp)
        video_temp = descargar_video_escena(escena["video_prompt"], num, escena["narracion"])
        
        if video_temp and os.path.exists(audio_temp):
            ruta_bloque = armar_bloque_escena(audio_temp, video_temp, escena["narracion"], num)
            bloques_renderizados.append(VideoFileClip(ruta_bloque))

    if bloques_renderizados:
        print("\n>>> [MOVIEPY] Uniendo capitulo final de René...")
        pelicula_completa = concatenate_videoclips(bloques_renderizados)
        pelicula_completa.write_videofile(archivo_pelicula_final, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        pelicula_completa.close()
        for b in bloques_renderizados: b.close()

        titulo = f"LA SERIE DE RENÉ ENRÍQUEZ 🧟‍♂️ (Capítulo Automático IA)"
        descripcion = f"Historia continua sobre el apocalipsis zombie.\n\nGenerado con Inteligencia Artificial."
        subir_a_youtube(archivo_pelicula_final, titulo, descripcion)
        print("[SISTEMA] Ciclo terminado con éxito.")
    else:
        print("[ERROR SISTEMA] No se pudieron fabricar los bloques mínimos.")

if __name__ == "__main__":
    asyncio.run(main())
