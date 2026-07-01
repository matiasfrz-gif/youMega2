import os
import random
import asyncio
import requests
import edge_tts
from google import genai
from moviepy import VideoFileClip, AudioFileClip,TextClip


# 🔐 CLAVES SÚPER SEGURAS
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")

# Si por alguna razón la consola de Windows no las cargó, las busca en un archivo local oculto
if not GEMINI_KEY:
    GEMINI_KEY = "AQ.Ab8RN6JVa8vZt7tGu8hNjVgxOri0n4vpDNaTriPV0_0zSdVJeQ"
if not PEXELS_KEY:
    PEXELS_KEY = "FAxCoyD8kp3eVyrPeQOQHSCjHkEYwswmKhPrSyTWAE65AS0yBeSFG37j"

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
    
    texto_original = response.text.strip()
    
    # Forzamos la conversión segura para evitar el error de caracteres de Windows
    texto_seguro = texto_original.encode('utf-8', errors='ignore').decode('utf-8')
    
    # 🧼 LIMPIADOR ULTRA PROFUNDO
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

    # 🔗 URL CORREGIDA CON LA BARRA EN SU LUGAR
    url = f"https://api.pexels.com/videos/search?query=f{tema}&orientation=portrait&per_page=5"
    headers = {"Authorization": PEXELS_KEY}
    
    try:
        response = requests.get(url, headers=headers).json()
        videos = response.get("videos", [])
        
        if videos:
            video_elegido = random.choice(videos)
            video_files = video_elegido.get("video_files", [])
            
            # Buscamos el link de descarga directo de forma segura
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

from moviepy import TextClip, CompositeVideoClip

def armar_video_final(archivo_audio, ruta_fondo, archivo_video_salida, texto_guion):
    print("\n>>> [MOVIEPY] Iniciando el montaje final con subtítulos...")
    
    if not ruta_fondo or not os.path.exists(ruta_fondo):
        print("[ERROR VIDEO] No se pudo obtener un video de fondo válido.")
        return

    video_clip = VideoFileClip(ruta_fondo)
    audio_clip = AudioFileClip(archivo_audio)
    
    # Cortamos el video de fondo a la duración exacta del audio
    duracion = audio_clip.duration
    video_recortado = video_clip.subclipped(0, duracion)
    
    # 📝 CREACIÓN DE SUBTÍTULOS AUTOMÁTICOS
    print("[MOVIEPY] Generando subtítulos en pantalla...")
    palabras = texto_guion.split()
    total_palabras = len(palabras)
    
    # Calculamos cuánto dura cada palabra aproximadamente en pantalla
    tiempo_por_palabra = duracion / total_palabras
    clips_de_texto = []
    
    # Agrupamos las palabras de a 3 para que no quede un texto gigante e incómodo
    grupo = []
    for i, palabra in enumerate(palabras):
        grupo.append(palabra)
        if len(grupo) == 3 or i == total_palabras - 1:
            texto_pantalla = " ".join(grupo).upper()
            
            # Calculamos el segundo exacto donde arranca y termina este grupo de palabras
            inicio_texto = (i - len(grupo) + 1) * tiempo_por_palabra
            fin_texto = (i + 1) * tiempo_por_palabra
            
            # Creamos el cartel de texto con MoviePy
            subtitulo = (TextClip(
                            text=texto_pantalla, 
                            font_size=50, 
                            color='yellow',
                            stroke_color='black', 
                            stroke_width=3
                         )
                         .with_start(inicio_texto)
                         .with_duration(fin_texto - inicio_texto)
                         .with_position(('center', 'center'))) # Lo clava justo en el medio
            
            clips_de_texto.append(subtitulo)
            grupo = [] # Vaciamos el grupo para las siguientes palabras
            
    # Pegamos el video recortado y todos los textos juntos uno arriba del otro
    video_con_subtitulos = CompositeVideoClip([video_recortado] + clips_de_texto)
    
    # Le sumamos el audio de la IA
    video_final = video_con_subtitulos.with_audio(audio_clip)
    
    print(f"[MOVIEPY] Exportando Short con subtítulos...")
    video_final.write_videofile(
        archivo_video_salida, 
        codec="libx264", 
        audio_codec="aac",
        fps=30,
        logger=None
    )
    
    # Cerramos los archivos para liberar memoria
        # Cerramos los archivos para liberar memoria
    video_clip.close()
    audio_clip.close()
    video_final.close()
    print(f"[SISTEMA] ¡Video creado con éxito!: {archivo_video_salida}")

async def main():
    print(">>> [YouMega2] Iniciando generador 100% Autónomo...")
    
    try:
        # 1. Intentamos usar la IA de Google normal
        tema, texto_guion = await obtener_guion_ia()
    except Exception:
        # 🛡️ Si Google está bloqueado por cuota, se activa este texto automático solo
        print("\n[AVISO] La IA de Google está al límite. Activando plan de respaldo...")
        tema = "el espacio exterior"
        texto_guion = "el espacio exterior esconde misterios increibles como estrellas que giran miles de veces por segundo en absoluto silencio"
        
    try:
        print(f"[GUION DETERMINADO]: '{texto_guion}'")
        
        # 2. Generamos el archivo de audio temporal
        archivo_audio = "audio_temporal.mp3"
        await generar_voz(texto_guion, archivo_audio)
        
        # 3. Descargamos o buscamos el fondo
        ruta_fondo = descargar_video_fondo(tema)
        
        # 4. Compilamos todo el Short pasándole el texto para los subtítulos
        video_salida = f"short_{tema.replace(' ', '_')}.mp4"
        armar_video_final(archivo_audio, ruta_fondo, video_salida, texto_guion)
        
        # 🧼 Limpieza del audio temporal
        if os.path.exists(archivo_audio):
            os.remove(archivo_audio)
            
        print("\n>>> [YouMega2] ¡Short creado con éxito de forma independiente!")
        
    except Exception as error_final:
        print(f"\n[ERROR GENERAL]: {error_final}")

if __name__ == "__main__":
    asyncio.run(main())

