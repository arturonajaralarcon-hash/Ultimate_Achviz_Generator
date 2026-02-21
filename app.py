import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import json
import os
import time
import numpy as np
from streamlit_drawable_canvas import st_canvas

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de imagen DeMos", layout="wide", page_icon="😸")

# --- FUNCIONES DE UTILIDAD ---
def upscale_image(image, target_width=3840): 
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), PIL.Image.Resampling.LANCZOS)
    return img_resized

def merge_canvas_drawing(bg_image, canvas_data):
    """Fusiona el dibujo del canvas (numpy array) con la imagen original PIL"""
    if canvas_data is None:
        return bg_image.convert("RGB")
    bg = bg_image.copy().convert("RGBA")
    drawing = PIL.Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
    # Redimensionar el dibujo al tamaño original de la imagen
    drawing = drawing.resize(bg.size, PIL.Image.Resampling.LANCZOS)
    bg.alpha_composite(drawing)
    return bg.convert("RGB")

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
try:
    PASSWORD_ACCESO = st.secrets["PASSWORD_ACCESO"]
except Exception:
    PASSWORD_ACCESO = "archviz2026" 

def check_password():
    if "authenticated" not in st.session_state:
        st.title("Acceso DeMos")
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
    st.title("Generador de Imagen DeMos")
    st.caption("ArchViz Specialized | Nano Banana Series & Imagen 3")

    with st.expander("📘 Glosario de Palabras Clave y Tutorial", expanded=False):
        st.markdown("""
        **Comandos principales:**
        * **Improve:** Mejora tu prompt.
        * **Improve edit:** Para usar con el Modo Dibujo. Escribe `Improve edit: <descripción>, Remove RED marked shapes`.
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
            "Imagen 4.0 (Generativo)" 
        ])
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image",
            "Imagen 4.0 (Generativo)": "imagen-4.0-generate-001" 
        }
    with c_controls_2:
        st.write("") 
        st.write("") 
        if st.button("Recargar JSONs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_controls_3:
        pass

    # --- ZONA 1: REFERENCIAS Y EDITOR ---
    st.subheader("1. Imagenes de referencia y Editor")
    uploaded_files = st.file_uploader("Sube fotos para analizar o editar (Modo Máscara)", 
                                     type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        for f in uploaded_files:
            img = PIL.Image.open(f)
            if not any(d['name'] == f.name for d in st.session_state.referencias):
                st.session_state.referencias.append({"img": img, "name": f.name})

    refs_activas = []
    if st.session_state.referencias:
        col_btn_limpiar, _ = st.columns([1, 4])
        if col_btn_limpiar.button("🗑️ Limpiar Biblioteca"):
            st.session_state.referencias = []
            st.rerun()
            
        cols_refs = st.columns(3) # 3 por fila para dar espacio al canvas
        for i, ref in enumerate(st.session_state.referencias):
            with cols_refs[i % 3]:
                with st.expander(f"🖼️ {ref['name'][:15]}...", expanded=False):
                    edit_mode = st.toggle("Modo Dibujo", key=f"tgl_{i}", help="Dibuja máscaras de color sobre la imagen")
                    
                    if edit_mode:
                        c_color, c_width = st.columns([1, 1])
                        color_name = c_color.selectbox("Pincel", ["Rojo", "Verde", "Azul", "Amarillo"], key=f"col_{i}")
                        color_map = {"Rojo": "#FF0000", "Verde": "#00FF00", "Azul": "#0000FF", "Amarillo": "#FFFF00"}
                        stroke_width = c_width.slider("Grosor", 1, 50, 15, key=f"wid_{i}")
                        
                        # Ajustar tamaño visual del canvas
                        w, h = ref["img"].size
                        ratio = h / w
                        disp_w = 280
                        disp_h = int(disp_w * ratio)
                        
                        st.caption("Usa la flecha circular del canvas para deshacer.")
                        canvas_result = st_canvas(
                            fill_color="rgba(0, 0, 0, 0)",
                            stroke_width=stroke_width,
                            stroke_color=color_map[color_name],
                            background_image=ref["img"],
                            height=disp_h,
                            width=disp_w,
                            drawing_mode="freedraw",
                            key=f"canvas_{i}"
                        )
                        
                        if st.checkbox("✅ Usar Editada", key=f"chk_edit_{i}"):
                            final_img = merge_canvas_drawing(ref["img"], canvas_result.image_data)
                            refs_activas.append(final_img)
                    else:
                        st.image(ref["img"], use_container_width=True)
                        if st.checkbox("✅ Usar Original", key=f"chk_orig_{i}"):
                            refs_activas.append(ref["img"].convert("RGB"))

    st.divider()

    # --- ZONA 2: ULTIMATE PROMPT ENGINE (LADO A LADO) ---
    st.subheader("2. Generador de Prompt")
    
    col_in, col_out = st.columns(2)
    
    # Columna Izquierda: Entrada
    with col_in:
        st.markdown("**1. Prompt inicial (Idea)**")
        cmd_input = st.text_area("Comando:", height=150, label_visibility="collapsed", 
                                 placeholder="Ej: Improve edit: foto de una sala, Remove RED marked shapes")
        btn_mejorar = st.button("✨ Procesar Idea", type="primary", use_container_width=True)

    # Columna Derecha: Salida del Modelo (Solo Lectura)
    with col_out:
        st.markdown("**2. Prompt mejorado (Traducción de IA)**")
        st.info(st.session_state.prompt_mejorado if st.session_state.prompt_mejorado else "La traducción estructurada aparecerá aquí...")

    # Lógica de mejora de prompt
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
                        st.session_state["fp_area"] = texto_limpio # Actualiza la caja de abajo
                        st.rerun()
                    else:
                        st.error("El modelo devolvió una respuesta vacía.")
                        
                except Exception as e:
                    st.error(f"Error en motor de prompts: {e}")
        else:
            st.warning("Escribe un comando primero.")

    # Fila inferior: Prompt Final Editable
    st.markdown("**3. Prompt Final (Ajuste Manual)**")
    final_prompt = st.text_area("Este es el texto que se enviará al Motor de Render:", 
                              value=st.session_state.prompt_final, 
                              height=120, 
                              key="fp_area")
    
    if final_prompt != st.session_state.prompt_final:
        st.session_state.prompt_final = final_prompt

    # --- ZONA 3: GENERACIÓN DE IMAGEN ---
    st.divider()
    
    if st.button("🚀 Renderizar Imagen", use_container_width=True):
        if st.session_state.prompt_final:
            with st.status("Procesando imagen...", expanded=False) as status:
                try:
                    prompt_render = f"High quality architectural visualization. {st.session_state.prompt_final}"
                    img_result = None

                    # CASO A: Imagen 3 / 4
                    if "imagen-" in model_map[modelo_nombre]:
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

                    # CASO B: Gemini Nano Banana
                    else:
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
                    
                    # PROCESAMIENTO FINAL: Guardar imagen + prompt
                    if img_result:
                        nuevo_registro = {
                            "img": img_result,
                            "prompt": st.session_state.prompt_final # Guardamos el prompt exacto
                        }
                        st.session_state.historial.insert(0, nuevo_registro)
                        if len(st.session_state.historial) > 10:
                            st.session_state.historial.pop()
                        
                        status.update(label="Renderizado completo", state="complete")
                        st.rerun()
                    else:
                        st.error("No se generó imagen (Posible filtro de seguridad).")
                        
                except Exception as e:
                    st.error(f"Error crítico: {e}")
        else:
            st.warning("El campo de prompt final está vacío.")

    # --- HISTORIAL CON BOTONES Y PROMPTS ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial de Sesión")
        
        cols = st.columns(3)
        for i, item in enumerate(st.session_state.historial):
            
            # Compatibilidad si había imágenes sueltas de la sesión anterior
            if isinstance(item, PIL.Image.Image):
                img = item
                prompt_txt = "Prompt no registrado"
            else:
                img = item["img"]
                prompt_txt = item["prompt"]
                
            with cols[i % 3]:
                st.image(img, use_container_width=True)
                
                # Cuadro de texto para mostrar el prompt (solo lectura)
                st.text_area("Prompt:", value=prompt_txt, height=80, disabled=True, key=f"txt_{i}", label_visibility="collapsed")
                
                c1, c2, c3 = st.columns([1, 1, 1])
                
                buf = BytesIO()
                img.save(buf, format="PNG")
                c1.download_button("💾", buf.getvalue(), f"demos_{i}.png", "image/png", key=f"dl_{i}")
                
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
