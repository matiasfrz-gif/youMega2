import os
import json
import random
import asyncio
import requests
import edge_tts
from google import genai
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

# 🔑 LIBRERÍAS DE YOUTUBE (API OFICIAL)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 RECOLECCIÓN DE TUS SECRETOS ACTUALES DE GITHUB
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

# Inicializamos Gemini con tu llave actual
client = genai.Client(api_key=GEMINI_KEY)

async def generar_voz_escena(texto, archivo_salida):
    try:
        # Una voz mexicana narrativa espectacular para historias de misterio/terror
        VOICE = "es-MX-JorgeNeural" 
        communicate = edge_tts.Communicate(texto, VOICE)
        await communicate.save(archivo_salida)
    except Exception as e:
        print(f"[AVISO] Voz principal falló en escena. Activando gTTS de respaldo...")
        from gtts import gTTS
        tts = gTTS(text=texto, lang='es', tld='com.mx')
        tts.save(archivo_salida)

async def obtener_guion_zombis_ia():
    ideas_apocalipsis = [
        "el escape de una zona de cuarentena militarizada en la ciudad",
        "un grupo de supervivientes atrapados en un centro comercial rodeado por la horda",
        "el descubrimiento del origen del virus en un laboratorio subterraneo abandonado",
        "una mision nocturna para conseguir suministros medicos en un hospital infectado"
    ]
    tema_elegido = random.choice(ideas_apocalipsis)
    print(f"\n[IA] Pidiéndole a Gemini una historia larga sobre: {tema_elegido}...")

    # Le pedimos que arme la estructura de bloques que pensaste
    prompt = (
        f"Escribe una historia de terror y ciencia ficcion de zombis basada en: {tema_elegido}. "
        f"La historia debe ser atrapante y detallada. "
        f"Divide la historia obligatoriamente en exactamente 10 escenas consecutivas para completar unos 5 minutos. "
        f"Devuelve el resultado UNICAMENTE en formato JSON limpio, sin bloques de codigo markdown (no uses ```json), "
        f"con la siguiente estructura exacta:\n"
        f"[\n"
        f"  {{\"escena\": 1, \"narracion\": \"Texto descriptivo de la escena sin acentos ni enies.\", \"video_prompt\": \"Palabras clave en ingles para buscar video de stock horizontal\"}},\n"
        f"  ... \n"
        f"]\n"
        f"REGLAS CRÍTICAS: No uses acentos ni letras enie (reemplaza nio por nia o nio). "
        f"El video_prompt debe ser en ingles para Pexels (ejemplo: 'zombie apocalypse city', 'dark abandoned hospital corridor')."
    )

    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    
    # Limpieza por si Gemini mete triples comillas de formato markdown
    texto_json = response.text.strip().replace("```json", "").replace("```", "")
    return tema_elegido, json.loads(texto_json)

def descargar_video_escena(prompt_video, num_escena):
    if not PEXELS_KEY:
        print("[ERROR] Falta configurar PEXELS_API_KEY.")
        return None

    os.makedirs("clips_temporales", exist_ok=True)
    ruta_guardado = os.path.join("clips_temporales", f"video_{num_escena}.mp4")

    # 🎬 CAMBIO DE ORIENTACIÓN: 'landscape' para formato cine/pantalla ancha de YouTube largo
    url = f"https://pexels.com{prompt_video}&orientation=landscape&per_page=3"
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
                video_data = requests.get(download_url).content
                with open(ruta_guardado, "wb") as f:
                    f.write(video_data)
                return ruta_guardado
    except Exception as e:
        print(f"[ERROR DESCARGA ESCENA {num_escena}]: {e}")
    return None

def armar_bloque_escena(archivo_audio, ruta_fondo, texto_narracion, num_escena):
    # Carga los recursos del "mini-short"
    video_clip = VideoFileClip(ruta_fondo)
    audio_clip = AudioFileClip(archivo_audio)
    duracion = audio_clip.duration

    # Ajusta duración del fondo si es muy corto
    if video_clip.duration < duracion:
        repeticiones = int(duracion / video_clip.duration) + 1
        video_extendido = concatenate_videoclips([video_clip] * repeticiones)
        video_recortado = video_extendido.subclipped(0, duracion)
    else:
        video_recortado = video_clip.subclipped(0, duracion)

    # Subtítulos adaptados para formato cine (abajo al centro, tamaño más grande 28)
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
     .with_position(('center', 'bottom'))) # Subtítulo abajo estilo película

    escena_montada = CompositeVideoClip([video_recortado, subtitulo]).with_audio(audio_clip)
    
    # Guardamos en disco el bloque intermedio renderizado para liberar RAM
    ruta_salida_bloque = os.path.join("clips_temporales", f"bloque_listo_{num_escena}.mp4")
    escena_montada.write_videofile(ruta_salida_bloque, codec="libx264", audio_codec="aac", fps=24, logger=None)
    
    # Cerramos clips para liberar memoria
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
                "tags": ["zombies", "historiasdeterror", "ia", "apocalipsis"],
                "categoryId": "24" # Categoría de Entretenimiento/Películas
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(archivo_video, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        print(f"[YOUTUBE API] Subiendo archivo largo...")
        response = request.execute()
        print(f"[SISTEMA] ¡Película subida con éxito! ID: {response.get('id')}")
    except Exception as e:
        print(f"[ERROR YOUTUBE API]: {e}")

# 🚀 COORDINADOR CENTRAL ASÍNCRONO
async def main():
    os.makedirs("clips_temporales", exist_ok=True)
    archivo_pelicula_final = "pelicula_zombies_final.mp4"

    # 1. Traer el guion en bloques estructurados de Gemini
    tema, lista_escenas = await obtener_guion_zombis_ia()
    
    bloques_renderizados = []

    # 2. Tu lógica: Procesar bloque por bloque ("como si fueran shorts independientes")
    for escena in lista_escenas:
        num = escena["escena"]
        print(f"\n--- TRABAJANDO EN ESCENA {num}/10 ---")
        
        audio_temp = os.path.join("clips_temporales", f"voz_{num}.mp3")
        
        # Generar audio de la escena
        await generar_voz_escena(escena["narracion"], audio_temp)
        
        # Descargar fondo horizontal de Pexels
        video_temp = descargar_video_escena(escena["video_prompt"], num)
        
        if video_temp and os.path.exists(audio_temp):
            # Ensamblar el mini-bloque y guardarlo
            ruta_bloque = armar_bloque_escena(audio_temp, video_temp, escena["narracion"], num)
            bloques_renderizados.append(VideoFileClip(ruta_bloque))

    # 3. 💥 UNIÓN FINAL: Pegamos todos los bloques uno detrás del otro
    if bloques_renderizados:
        print("\n>>> [MOVIEPY] Concatenando todos los bloques en la película final...")
        pelicula_completa = concatenate_videoclips(bloques_renderizados)
        pelicula_completa.write_videofile(archivo_pelicula_final, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        # Cerrar archivos para que no queden bloqueados
        pelicula_completa.close()
        for b in bloques_renderizados: b.close()

        # 4. Subir el resultado final a YouTube usando tus credenciales guardadas
        titulo = f"APOCALIPSIS: {tema.upper()} 🧟‍♂️ (Historia de Terror IA)"
        descripcion = f"Una experiencia cinematografica inmersiva sobre supervivencia zombie en un mundo destruido.\n\nGenerado automaticamente en la nube."
        subir_a_youtube(archivo_pelicula_final, titulo, descripcion)
        
        print("[SISTEMA] Flujo terminado en la nube de GitHub con éxito.")
    else:
        print("[ERROR SISTEMA] No se pudieron fabricar los bloques mínimos.")

if __name__ == "__main__":
    asyncio.run(main())
