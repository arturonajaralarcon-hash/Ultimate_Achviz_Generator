import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import json
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de imagen DeMos", layout="wide", page_icon="😸")

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
if "prompt_final" not in st.session_state:
    st.session_state.prompt_final = ""
if "json_data" not in st.session_state:
    data, msg = load_json_data()
    st.session_state.json_data = data
    st.session_state.json_msg = msg

# --- SEGURIDAD ---
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
    st.caption("ArchViz Specialized | Nano Banana Series")

    # --- TEXTO DE BIENVENIDA / TUTORIAL ---
    with st.expander("📘 Glosario de Palabras Clave y Tutorial (PromptAssistantGEM)", expanded=False):
        st.markdown("""
        **Para ayudarte a comenzar, aquí tienes una lista de las palabras clave disponibles y sus funciones dentro del sistema PromptAssistantGEM:**

        ### Glosario de Palabras Clave
        * **Help:** Proporciona esta lista de palabras clave y explica brevemente sus funciones.
        * **Set / Settings:** Muestra los parámetros fijos activos (como la relación de aspecto) y permite modificarlos.
        * **Platform:** Cambia la plataforma de IA específica para la cual se escriben los prompts (ej. Midjourney, DALL-E, Gemini).
        * **Improve:** Mejora un prompt simple del usuario convirtiéndolo en una versión detallada y de alta calidad.
        * **Improve edit:** Un activador especializado para la edición de imágenes. Traduce comandos basados en formas (como "Eliminar ROJO") en instrucciones detalladas.
        * **Multiple:** Genera varias opciones diferentes del mismo prompt. Ejemplo: Multiple: 3.
        * **Chance:** Modifica el prompt o añade texto según se solicite. Fórmula: cambios + (to) 'prompt original'.
        * **Describe:** Analiza una imagen cargada y la convierte en un prompt basado en una categoría. Ejemplo: Describe + architectural.
        * **Reference:** Toma características específicas de una imagen cargada (paleta de colores, atmósfera) para usarlas en el siguiente prompt.
        * **Original:** Devuelve y une todos los prompts iniciales y cambios realizados durante la sesión.
        * **Question:** Responde dudas sobre ingeniería de prompts y ofrece recomendaciones específicas.
        * **Clear / clean:** Olvida todo el trabajo anterior y comienza desde cero.

        ### Categorías Especializadas
        Si tu prompt comienza con *Architectural* o *Interior Design*, el asistente utiliza "Recetas" específicas:
        * **Architectural Recipe:** Incluye Ángulo de cámara, Tipo de imagen, Estilo, Tipo de edificio, Inspiración, Punto focal, Materiales, Iluminación y Estado de ánimo.
        * **Interior Design Recipe:** Incluye Ángulo de cámara, Tipo de habitación, Estilo, Marca, Punto focal, Texturas e Iluminación.
        * **Brainstorm / Brainstorming:** Ofrece ideas congruentes y creativas para mejorar el prompt.
        * **Missing Parts:** Identifica parámetros faltantes y sugiere mejoras para completarlos.

        ### Tutorial Corto
        1.  **Define tus Ajustes:** Comienza indicando si prefieres una relación de aspecto.
        2.  **Combina Palabras Clave:** "Reference: color palette, Improve: un gato negro durmiendo en un sofá. Multiple: 2".
        3.  **Refina Ediciones:** "Improve edit: una foto de un escritorio, Remove RED marked shapes, insert in BLUE a vintage laptop".
        
        *¿Cómo te gustaría empezar? ¿Deseas aplicar algún ajuste predeterminado para esta sesión?*
        """)
        
        # Estado de carga de JSONs
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
            "Nano Banana (Gemini 2.5 Flash Image)"
        ])
        model_map = {
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Image)": "gemini-2.5-flash-image"
        }

    with c_controls_2:
        st.write("") 
        st.write("") 
        if st.button("Recargar JSONs", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    with c_controls_3:
        pass

    # --- ZONA 1: REFERENCIAS ---
    st.subheader("1. Imagenes de referencia")
    uploaded_files = st.file_uploader("Sube fotos a editar o referencias de estilo", 
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

    st.divider()

# --- ZONA 2: ULTIMATE PROMPT ENGINE (VERTICAL) ---
    st.subheader("2. Generador de Prompt")
    
    # 2.1 Entrada
    st.markdown("**Prompt inicial**")
    cmd_input = st.text_area("Escribe tu prompt (ej: 'Architectural: Museo moderno' o 'Improve: casa de playa')", height=100)
    
    # 2.2 Botón de Acción
    if st.button("Mejorar Prompt", type="primary", use_container_width=True):
        if cmd_input:
            with st.spinner("Mejorando Prompt..."):
                try:
                    # Preparamos contexto
                    json_context = json.dumps(st.session_state.json_data, indent=2, ensure_ascii=False) if st.session_state.json_data else "No JSON data."
                    
                    # Prompt del Sistema
                    system_prompt = f"""
                    You are 'PromptAssistantGEM', an advanced CLI for ArchViz Prompt Engineering.
                    I have loaded a library of styles/materials in JSON:
                    {json_context}

                    YOUR RULES BASED ON USER GLOSSARY:
                    1. 'Improve:': Convert simple input into high-quality detailed prompt using JSON terms.
                    2. 'Architectural Recipe': Must include Camera Angle, Image Type, Style, Building Type, Inspiration, Focal Point, Materials, Lighting, Mood.
                    3. 'Interior Design Recipe': Must include Camera Angle, Room Type, Style, Brand, Focal Point, Textures, Lighting.
                    4. 'Platform:': Optimize terminology for the specified AI (Midjourney, Gemini, etc).
                    5. 'Multiple:': If requested, provide options.
                    
                    TASK: Analyze the USER COMMAND and output ONLY the final optimized prompt text ready for rendering.
                    
                    USER COMMAND: {cmd_input}
                    """
                    
                    # Llamada a Gemini Flash (Texto)
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=system_prompt
                    )
                    
                    # Validación de respuesta de TEXTO
                    if res.text:
                        texto_limpio = res.text.strip()
                        
                        # 1. Actualizamos la variable maestra
                        st.session_state.prompt_final = texto_limpio
                        
                        # 2. !!! ESTA ES LA SOLUCIÓN !!!
                        # Forzamos la actualización directa de la memoria del widget "fp_area"
                        st.session_state["fp_area"] = texto_limpio
                        
                        # 3. Recargamos para que el cambio se vea inmediatamente
                        st.rerun()
                    else:
                        st.error("El modelo devolvió una respuesta vacía.")
                        
                except Exception as e:
                    st.error(f"Error en motor de prompts: {e}")
        else:
            st.warning("Escribe un comando primero.")

    # 2.3 Salida
    st.markdown("**Prompt Final (Editable)**")
    
    # Nos aseguramos que la variable prompt_final tenga algo antes de pintar
    if "prompt_final" not in st.session_state:
        st.session_state.prompt_final = ""

    final_prompt = st.text_area("Resultado optimizado:", 
                              value=st.session_state.prompt_final, 
                              height=150, 
                              key="fp_area") # La clave 'fp_area' ahora ya tiene el valor inyectado
    
    # Sincronización inversa: Si el usuario edita a mano, actualizamos el estado
    if final_prompt != st.session_state.prompt_final:
        st.session_state.prompt_final = final_prompt
    # --- ZONA 3: GENERACIÓN DE IMAGEN ---
    st.divider()
    
    if st.button("Crear Imagen", use_container_width=True):
        if st.session_state.prompt_final:
            with st.status("Renderizando...", expanded=False) as status:
                try:
                    prompt_render = f"High quality architectural visualization. {st.session_state.prompt_final}"
                    contenido_solicitud = [prompt_render] + refs_activas
                    
                    response = client.models.generate_content(
                        model=model_map[modelo_nombre],
                        contents=contenido_solicitud,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"]
                        )
                    )
                    
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
                            st.error("No se generó imagen (Posible filtro de seguridad).")
                    else:
                        st.error("Error API.")
                        
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
