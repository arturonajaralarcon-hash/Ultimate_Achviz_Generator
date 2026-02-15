import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import json
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Image Gen DeMos", layout="wide", page_icon="🏗️")

# --- CARGADOR DE DATOS JSON (ESTILOS Y MATERIALES) ---
@st.cache_data
def load_json_data(folder_path="data"):
    """
    Carga bibliotecas de estilos, iluminación y cámaras desde la carpeta 'data'.
    Ideal para ArchViz: styles.json, materials.json, lighting.json
    """
    data_context = {}
    
    if not os.path.exists(folder_path):
        return None, "⚠️ Carpeta 'data' no encontrada. Crea la carpeta en tu proyecto."
    
    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    
    if not files:
        return None, "⚠️ Carpeta 'data' vacía. Sube tus JSONs de estilos."

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
if "prompt_final" not in st.session_state:
    st.session_state.prompt_final = ""
if "json_data" not in st.session_state:
    data, msg = load_json_data()
    st.session_state.json_data = data
    st.session_state.json_msg = msg

# --- SEGURIDAD (Regresamos a la clave de DeMos) ---
PASSWORD_ACCESO = "archviz2026"

def check_password():
    if "authenticated" not in st.session_state:
        st.sidebar.title("Acceso DeMos")
        pwd = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Entrar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.sidebar.error("Incorrecta")
        return False
    return True

if check_password():
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    # --- ENCABEZADO ---
    st.title("Image Gen DeMos 🏗️")
    st.caption("ArchViz Specialized | Nano Banana Series + Ultimate Prompt Engine")

    with st.expander("📘 Guía de Comandos ArchViz", expanded=True):
        st.markdown("""
        **Motor de Mejora de Prompts para Arquitectura.**
        Usa tus archivos JSON para generar descripciones técnicas precisas.

        **Comandos:**
        * `improve: <idea>` -> Aplica terminología técnica (Iluminación, Materiales, Cámara) basada en tus JSONs.
        * `style: <estilo>` -> Busca estilos específicos (ej: Brutalism, Parametric) en tu base de datos.
        * `edit: <texto>` -> Ajustes rápidos de redacción.
        """)
        
        if st.session_state.json_msg and "✅" in st.session_state.json_msg:
            st.success(st.session_state.json_msg)
        else:
            st.warning(st.session_state.json_msg or "Cargando...")

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("Ajustes de Render")
        modelo_nombre = st.selectbox("Motor", [
            "Nano Banana Pro (Gemini 3 Pro Image)",
            "Nano Banana (Gemini 2.5 Flash Image)"
        ])
        
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image"
        }
        
        if st.button("Recargar JSONs 🔄"):
            st.cache_data.clear()
            st.rerun()

    # --- ZONA 1: BIBLIOTECA DE REFERENCIAS (Visual Context) ---
    st.subheader("1. Contexto Visual")
    uploaded_files = st.file_uploader("Arrastra planos, bocetos o referencias de estilo", 
                                     type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        for f in uploaded_files:
            img = PIL.Image.open(f)
            if not any(d['name'] == f.name for d in st.session_state.referencias):
                st.session_state.referencias.append({"img": img, "name": f.name})

    refs_activas = []
    if st.session_state.referencias:
        cols = st.columns(6)
        for i, ref in enumerate(st.session_state.referencias):
            with cols[i % 6]:
                st.image(ref["img"], use_container_width=True)
                if st.checkbox(f"Usar", key=f"check_{ref['name']}"):
                    refs_activas.append(ref["img"])
        if st.button("Limpiar Biblioteca"):
            st.session_state.referencias = []
            st.rerun()
    else:
        st.info("Sin referencias cargadas. Se generará renderizado 'Zero-shot' (solo texto).")

    st.divider()

    # --- ZONA 2: ULTIMATE PROMPT ENGINE (Lógica JSON para Arquitectura) ---
    st.subheader("2. Composición de Prompt")
    
    col_input, col_output = st.columns(2)
    
    with col_input:
        cmd_input = st.text_area("Comando (ej: improve: museo de arte moderno en el desierto):", height=150)
        
        if st.button("Mejorar Prompt 🪄", type="primary"):
            if cmd_input:
                with st.spinner("Consultando biblioteca de materiales y luces..."):
                    try:
                        # Preparamos los datos JSON para el prompt del sistema
                        json_context = json.dumps(st.session_state.json_data, indent=2, ensure_ascii=False) if st.session_state.json_data else "No specific JSON data."
                        
                        # Prompt especializado en Arquitectura
                        system_prompt = f"""
                        You are an Expert Architectural Visualization Prompt Engineer.
                        I have loaded a library of architectural styles, materials, and lighting in JSON format:
                        {json_context}

                        YOUR TASK:
                        Analyze the user command.
                        1. If command is 'improve:': Create a photorealistic ArchViz prompt. Use specific terms from the JSON data (e.g., specific concrete types, glass properties, camera lenses).
                        2. Structure: Subject (Building/Interior) + Architecture Style + Environment/Lighting + Materials + Technical Specs (Renderer, Resolution).
                        3. Output ONLY the final prompt text.

                        USER COMMAND: {cmd_input}
                        """
                        
                        # Usamos Flash para la lógica de texto
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=system_prompt
                        )
                        st.session_state.prompt_final = res.text.strip()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en motor de prompts: {e}")
            else:
                st.warning("Escribe una idea base.")

    with col_output:
        st.markdown("**Prompt Final (Editable)**")
        final_prompt = st.text_area("Resultado para Render:", 
                                  value=st.session_state.prompt_final, 
                                  height=150, 
                                  key="fp_area")
        
        if final_prompt != st.session_state.prompt_final:
            st.session_state.prompt_final = final_prompt

    # --- ZONA 3: GENERACIÓN ---
    st.divider()
    
    if st.button("Generar Render ✨", use_container_width=True):
        if st.session_state.prompt_final:
            with st.status("Procesando imagen...", expanded=False) as status:
                try:
                    # Construcción de la solicitud
                    # Para DeMos, simplemente combinamos el prompt técnico + las referencias visuales
                    prompt_render = f"High quality architectural visualization. {st.session_state.prompt_final}"
                    
                    contenido_solicitud = [prompt_render] + refs_activas
                    
                    # Llamada al modelo
                    response = client.models.generate_content(
                        model=model_map[modelo_nombre],
                        contents=contenido_solicitud,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"]
                        )
                    )
                    
                    # Validación
                    if response and response.parts:
                        img_result = None
                        for part in response.parts:
                            if part.inline_data:
                                img_result = PIL.Image.open(BytesIO(part.inline_data.data))
                                break
                        
                        if img_result:
                            st.session_state.historial.insert(0, img_result)
                            if len(st.session_state.historial) > 10:
                                st.session_state.historial.pop()
                            
                            st.subheader("Resultado")
                            st.image(img_result, use_container_width=True, caption="Render DeMos")
                            status.update(label="Renderizado completo", state="complete")
                        else:
                            st.error("El modelo no generó imagen. Posible filtro de seguridad o prompt muy complejo.")
                    else:
                        st.error("Error de API: Respuesta vacía.")
                        
                except Exception as e:
                    st.error(f"Error crítico: {e}")
        else:
            st.warning("El campo de prompt final está vacío.")

    # --- HISTORIAL ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial Reciente")
        cols = st.columns(5)
        for i, img in enumerate(st.session_state.historial):
            with cols[i % 5]:
                st.image(img, use_container_width=True)
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾", buf.getvalue(), f"demos_render_{i}.png", "image/png", key=f"d{i}")
