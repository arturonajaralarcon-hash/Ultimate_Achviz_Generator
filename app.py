import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import json
import os
import time

# ==========================================
# 1. CONFIGURACIÓN VISUAL (ESTILO TÉCNICO)
# ==========================================
st.set_page_config(page_title="Archviz Specialist", layout="wide", page_icon="▪️")

st.markdown("""
<style>
    /* TIPOGRAFÍA TÉCNICA */
    p, h1, h2, h3, h4, h5, h6, div, span, label, button, input, textarea, li {
        font-family: 'Consolas', 'Courier New', monospace;
    }

    /* VARIABLES DE COLOR (ADAPTATIVO) */
    :root {
        --fondo-app: #EAEAEA;
        --texto-app: #333333;
        --fondo-input: #FFFFFF;
        --borde: #333333;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --fondo-app: #333333;
            --texto-app: #EAEAEA;
            --fondo-input: #444444;
            --borde: #EAEAEA;
        }
    }

    /* ESTILOS GENERALES */
    .stApp { background-color: var(--fondo-app); color: var(--texto-app); }
    p, h1, h2, h3, h4, label, li, .stMarkdown { color: var(--texto-app) !important; }

    /* BOTONES */
    button, div.stButton > button, div.stDownloadButton > button, [data-testid="stFileUploader"] button {
        background-color: transparent !important;
        color: var(--texto-app) !important;
        border: 2px dashed var(--borde) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
        text-transform: uppercase;
        font-weight: bold;
    }
    button:hover, div.stButton > button:hover, div.stDownloadButton > button:hover, [data-testid="stFileUploader"] button:hover {
        background-color: var(--borde) !important;
        color: var(--fondo-app) !important;
        border-style: solid !important;
    }

    /* INPUTS */
    .stTextInput > div > div, div[data-baseweb="select"] > div, .stTextArea > div > div {
        background-color: var(--fondo-input) !important;
        border: 1px solid var(--borde) !important;
        color: var(--texto-app) !important;
    }
    .stTextInput input, .stTextArea textarea { color: var(--texto-app) !important; }
    
    /* DROPDOWNS */
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: var(--fondo-input) !important;
        border: 1px solid var(--borde) !important;
    }
    div[data-baseweb="option"], li[data-baseweb="option"] { color: var(--texto-app) !important; }

    /* FILE UPLOADER */
    [data-testid="stFileUploader"] {
        background-color: var(--fondo-input) !important;
        border: 1px dashed var(--borde) !important;
    }
    [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small {
        color: var(--texto-app) !important;
    }

    /* EXPANDER */
    .streamlit-expanderHeader {
        background-color: var(--fondo-input) !important;
        color: var(--texto-app) !important;
        border: 1px dashed var(--borde) !important;
    }
    .streamlit-expanderContent {
        border: 1px dashed var(--borde) !important;
        border-top: none;
        color: var(--texto-app) !important;
    }
    .streamlit-expanderHeader svg { fill: var(--texto-app) !important; }
    
    /* BARRA PROGRESO */
    .stProgress > div > div > div > div { background-color: var(--texto-app) !important; }
    
    hr { border-top: 1px solid var(--borde) !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE UTILIDAD ---
def upscale_image(image, target_width=3840): 
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), PIL.Image.Resampling.LANCZOS)
    return img_resized

# NUEVA FUNCIÓN: Traductor estricto para Veo 3.1
def pil_to_veo_image(pil_img):
    buf = BytesIO()
    # Aseguramos que sea RGB para guardarla como JPEG
    pil_img.convert("RGB").save(buf, format="JPEG")
    return types.Image(
        image_bytes=buf.getvalue(),
        mime_type="image/jpeg"
    )

# --- CARGADOR DE DATOS JSON ---
@st.cache_data
def load_json_data(folder_path="data"):
    data_context = {}
    if not os.path.exists(folder_path):
        return None, "⚠️ Carpeta 'data' no encontrada."
    
    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    if not files:
        return None, "⚠️ Carpeta 'data' vacía."

    try:
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                category_name = filename.replace('.json', '')
                data_context[category_name] = json.load(f)
        return data_context, f"✅ Biblioteca ArchViz cargada ({len(files)} archivos)."
    except Exception as e:
        return None, f"Error leyendo JSONs: {e}"

# --- ESTADOS DE SESIÓN ---
if "referencias" not in st.session_state:
    st.session_state.referencias = [] 
if "historial" not in st.session_state:
    st.session_state.historial = []
if "prompt_mejorado" not in st.session_state:
    st.session_state.prompt_mejorado = ""
if "prompt_final" not in st.session_state:
    st.session_state.prompt_final = ""
if "json_data" not in st.session_state:
    data, msg = load_json_data()
    st.session_state.json_data = data
    st.session_state.json_msg = msg

# --- SEGURIDAD ---
PASSWORD_ACCESO = st.secrets["PASSWORD_ACCESO"]

def check_password():
    if "authenticated" not in st.session_state:
        st.title("Acceso")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrecta")
        return False
    return True

if check_password():
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    # --- ENCABEZADO ---
    st.title("Ultimate Archviz Generator")
    st.caption("ArchViz Specialized | Nano Banana, Imagen 3 & Veo 3.1 Video")

    with st.expander("📘 Glosario de Palabras Clave y Tutorial", expanded=False):
        st.markdown("""
        **Comandos principales:**
        * **Improve:** Mejora tu prompt.
        * **Improve edit:** Ideal para editar. Usa Paint para pintar áreas y escribe: `Improve edit: <descripción>, Remove RED marked shapes`.
        * **Architectural / Interior Design Recipe:** Usa las fórmulas maestras.
        """)
        if st.session_state.json_msg and "✅" in st.session_state.json_msg:
            st.success(st.session_state.json_msg)
        else:
            st.warning(st.session_state.json_msg or "Cargando JSONs...")
    st.divider()

    # --- CONTROLES SUPERIORES ---
    c_controls_1, c_controls_2, c_controls_3 = st.columns([2, 1, 1])
    with c_controls_1:
        modelo_nombre = st.selectbox("Motor de Render", [
            "Nano Banana Pro (Gemini 3 Pro Image)",
            "Nano Banana (Gemini 2.5 Flash Image)",
            "Imagen 4.0 (Generativo)",
            "Veo 3.1 (Video Generativo)" 
        ])
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image",
            "Imagen 4.0 (Generativo)": "imagen-4.0-generate-001",
            "Veo 3.1 (Video Generativo)": "veo-3.1-generate-preview" 
        }
    with c_controls_2:
        st.write("") 
        st.write("") 
        if st.button("Recargar JSONs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_controls_3:
        pass
        
    # --- ZONA 1: REFERENCIAS Y PORTAPAPELES ---
    st.subheader("1. Referencias Visuales")
    
    uploaded_files = st.file_uploader("Sube o pega tus fotos aquí", 
                                     type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        for f in uploaded_files:
            img = PIL.Image.open(f)
            if not any(d['name'] == f.name for d in st.session_state.referencias):
                st.session_state.referencias.append({"img": img, "name": f.name})

    refs_activas = []
    if st.session_state.referencias:
        col_btn_limpiar, _ = st.columns([1, 4])
        if col_btn_limpiar.button("🗑️ Limpiar Referencias"):
            st.session_state.referencias = []
            st.rerun()
            
        cols_refs = st.columns(6) 
        for i, ref in enumerate(st.session_state.referencias):
            with cols_refs[i % 6]:
                st.image(ref["img"], use_container_width=True)
                if st.checkbox("Usar", key=f"chk_orig_{i}"):
                    refs_activas.append(ref["img"].convert("RGB"))

    st.divider()

    # --- ZONA 2: ULTIMATE PROMPT ENGINE (LADO A LADO) ---
    st.subheader("2. Generador de Prompt")
    
    col_in, col_out = st.columns(2)
    
    with col_in:
        st.markdown("**1. Prompt inicial (Idea)**")
        cmd_input = st.text_area("Comando:", height=150, label_visibility="collapsed", 
                                 placeholder="Ej: Improve edit: foto de una sala, Remove RED marked shapes")
        btn_mejorar = st.button("✨ Procesar Idea", type="primary", use_container_width=True)

    with col_out:
        st.markdown("**2. Prompt mejorado (Traducción de IA)**")
        st.info(st.session_state.prompt_mejorado if st.session_state.prompt_mejorado else "La traducción estructurada aparecerá aquí...")

    if btn_mejorar:
        if cmd_input:
            with st.spinner("Consultando bases de datos..."):
                try:
                    json_context = json.dumps(st.session_state.json_data, indent=2, ensure_ascii=False) if st.session_state.json_data else "No JSON data."
                    
                    system_prompt = f"""
                    You are 'PromptAssistantGEM', an advanced CLI for ArchViz Prompt Engineering.
                    I have loaded a library of styles/materials in JSON:
                    {json_context}

                    YOUR RULES BASED ON USER GLOSSARY:
                    1. 'Improve:': Convert simple input into high-quality detailed prompt using JSON terms.
                    2. 'Architectural Recipe': Must include Camera Angle, Image Type, Style, Building Type, Inspiration, Focal Point, Materials, Lighting, Mood.
                    3. 'Interior Design Recipe': Must include Camera Angle, Room Type, Style, Brand, Focal Point, Textures, Lighting.
                    4. 'Platform:': Optimize terminology for the specified AI.
                    5. 'Multiple:': If requested, provide options.
                    6. 'Improve edit:': Translate shape-based commands using colors (Red, Blue, etc.) into strict instructions for image editing.
                    
                    TASK: Analyze the USER COMMAND and output ONLY the final optimized prompt text ready for rendering.
                    
                    USER COMMAND: {cmd_input}
                    """
                    
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=system_prompt
                    )
                    
                    if res.text:
                        texto_limpio = res.text.strip()
                        st.session_state.prompt_mejorado = texto_limpio
                        st.session_state.prompt_final = texto_limpio
                        st.session_state["fp_area"] = texto_limpio 
                        st.rerun()
                    else:
                        st.error("El modelo devolvió una respuesta vacía.")
                        
                except Exception as e:
                    st.error(f"Error en motor de prompts: {e}")
        else:
            st.warning("Escribe un comando primero.")

    st.markdown("**3. Prompt Final (Ajuste Manual)**")
    final_prompt = st.text_area("Este es el texto que se enviará al Motor de Render:", 
                              value=st.session_state.prompt_final, 
                              height=120, 
                              key="fp_area")
    
    if final_prompt != st.session_state.prompt_final:
        st.session_state.prompt_final = final_prompt

    # --- ZONA 3: GENERACIÓN DE IMAGEN / VIDEO ---
    st.divider()
    
    if st.button("🚀 Renderizar (Imagen / Video)", use_container_width=True):
        if st.session_state.prompt_final:
            with st.status("Procesando...", expanded=True) as status:
                try:
                    prompt_render = f"High quality architectural visualization. {st.session_state.prompt_final}"
                    img_result = None
                    video_result_path = None

                    # CASO A: Imagen 3 / 4
                    if "imagen-" in model_map[modelo_nombre]:
                        status.update(label="Generando imagen con Imagen 4.0...", state="running")
                        response = client.models.generate_images(
                            model=model_map[modelo_nombre],
                            prompt=prompt_render,
                            config=types.GenerateImagesConfig(
                                number_of_images=1,
                                aspect_ratio="16:9" 
                            )
                        )
                        if response and response.generated_images:
                            img_result = response.generated_images[0].image._pil_image

                    # CASO B: Video con Veo 3.1
                    elif "veo-" in model_map[modelo_nombre]:
                        status.update(label="🎬 Iniciando generación de video (Esto puede tardar varios minutos)...", state="running")
                        
                        video_kwargs = {
                            "model": model_map[modelo_nombre],
                            "prompt": prompt_render,
                        }
                        
                        # ¡CORRECCIÓN AQUÍ! Pasamos la imagen por nuestro traductor pil_to_veo_image
                        if refs_activas:
                            video_kwargs["image"] = pil_to_veo_image(refs_activas[0])
                            
                            if len(refs_activas) > 1:
                                video_kwargs["config"] = types.GenerateVideosConfig(
                                    reference_images=[pil_to_veo_image(img) for img in refs_activas[1:]]
                                )

                        operation = client.models.generate_videos(**video_kwargs)
                        
                        while not operation.done:
                            status.update(label="Procesando video con Veo3... Por favor espera ⏳", state="running")
                            time.sleep(10)
                            operation = client.operations.get(operation)
                            
                        status.update(label="Descargando el video generado...", state="running")
                        
                        if operation.response and operation.response.generated_videos:
                            generated_video = operation.response.generated_videos[0]
                            video_path = f"archviz_video_{int(time.time())}.mp4"
                            
                            client.files.download(file=generated_video.video)
                            generated_video.video.save(video_path)
                            video_result_path = video_path

                    # CASO C: Gemini Nano Banana (Flash/Pro)
                    else:
                        status.update(label="Generando imagen con Nano Banana...", state="running")
                        contenido_solicitud = [prompt_render] + refs_activas
                        response = client.models.generate_content(
                            model=model_map[modelo_nombre],
                            contents=contenido_solicitud,
                            config=types.GenerateContentConfig(
                                response_modalities=["IMAGE"]
                            )
                        )
                        
                        if response and response.parts:
                            for part in response.parts:
                                if part.inline_data:
                                    img_result = PIL.Image.open(BytesIO(part.inline_data.data))
                                    break
                    
                    # PROCESAMIENTO FINAL: Guardar en historial
                    if img_result or video_result_path:
                        nuevo_registro = {
                            "type": "video" if video_result_path else "image",
                            "img": img_result, 
                            "file_path": video_result_path, 
                            "prompt": st.session_state.prompt_final 
                        }
                        st.session_state.historial.insert(0, nuevo_registro)
                        if len(st.session_state.historial) > 10:
                            st.session_state.historial.pop()
                        
                        status.update(label="¡Proceso completo!", state="complete")
                        st.rerun()
                    else:
                        st.error("No se generó contenido. Revisa si la respuesta fue bloqueada por filtros de seguridad.")
                        
                except Exception as e:
                    st.error(f"Error crítico durante la generación: {e}")
        else:
            st.warning("El campo de prompt final está vacío.")

    # --- HISTORIAL CON BOTONES Y PROMPTS ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial de Sesión")
        
        cols = st.columns(3)
        for i, item in enumerate(st.session_state.historial):
            
            is_video = False
            if isinstance(item, dict):
                is_video = item.get("type") == "video"
                img = item.get("img")
                prompt_txt = item.get("prompt", "Prompt no registrado")
                video_path = item.get("file_path")
            else:
                img = item
                prompt_txt = "Prompt no registrado"
                
            with cols[i % 3]:
                # --- SI ES VIDEO ---
                if is_video:
                    if video_path and os.path.exists(video_path):
                        st.video(video_path)
                        st.text_area("Prompt:", value=prompt_txt, height=80, disabled=True, key=f"txt_{i}", label_visibility="collapsed")
                        
                        c1, c2 = st.columns([1, 1])
                        with open(video_path, "rb") as f:
                            c1.download_button("💾 Guardar MP4", f, file_name=f"archviz_vid_{i}.mp4", mime="video/mp4", key=f"dl_{i}")
                    else:
                        st.error("Archivo de video no encontrado en disco.")
                
                # --- SI ES IMAGEN ---
                else:
                    if img:
                        st.image(img, use_container_width=True)
                        st.text_area("Prompt:", value=prompt_txt, height=80, disabled=True, key=f"txt_{i}", label_visibility="collapsed")
                        
                        c1, c2, c3 = st.columns([1, 1, 1])
                        
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        c1.download_button("💾", buf.getvalue(), f"archviz_{i}.png", "image/png", key=f"dl_{i}")
                        
                        if c2.button("🔍 4K", key=f"up_{i}"):
                            with st.spinner("Reescalando..."):
                                img_4k = upscale_image(img)
                                buf_4k = BytesIO()
                                img_4k.save(buf_4k, format="PNG", optimize=True)
                                st.session_state[f"ready_4k_{i}"] = buf_4k.getvalue()
                                st.rerun()
                        
                        if f"ready_4k_{i}" in st.session_state:
                            c2.download_button("⬇️", st.session_state[f"ready_4k_{i}"], f"4k_{i}.png", "image/png", key=f"dl4k_{i}")

                        if c3.button("🔄 Ref", key=f"ref_{i}"):
                            st.session_state.referencias.append({
                                "img": img,
                                "name": f"hist_{int(time.time())}.png"
                            })
                            st.toast("Añadida a Referencias", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
