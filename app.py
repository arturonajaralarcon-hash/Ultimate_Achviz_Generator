import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO
import uuid

# Configuracion de pagina profesional
st.set_page_config(page_title="ArchViz DeMos, powered by Gemini Pro", layout="wide")

# --- INICIALIZACION DE ESTADOS ---
if "referencias" not in st.session_state:
    st.session_state.referencias = {} # {id: {image: PIL, name: str}}
if "historial" not in st.session_state:
    st.session_state.historial = [] # Lista de objetos PIL

# --- SEGURIDAD ---
PASSWORD_ACCESO = "archviz2026"

def check_password():
    if "authenticated" not in st.session_state:
        st.sidebar.title("Acceso")
        pwd = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Entrar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.sidebar.error("Credencial incorrecta")
        return False
    return True

if check_password():
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    st.title("Image Gen DeMos")
    st.caption("ArchViz Engine | High-End Architectural Visualization")

    # --- SIDEBAR: PANEL DE CONTROL ---
    with st.sidebar:
        st.header("Configuracion Tecnica")
        
        modelo_nombre = st.selectbox("Motor de Render", [
            "Imagen 4 Ultra Generate",
            "Imagen 4 Generate",
            "Nano Banana Pro (Gemini 3 Pro Image)",
            "Nano Banana (Gemini 2.5 Flash Preview Image)"
        ])
        
        model_map = {
            "Imagen 4 Ultra Generate": "imagen-4.0-ultra-generate-001",
            "Imagen 4 Generate": "imagen-4.0-generate-001",
            "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
            "Nano Banana (Gemini 2.5 Flash Preview Image)": "gemini-2.5-flash-image"
        }
        
        st.subheader("Formato")
        aspect_ratio = st.selectbox("Aspect Ratio", [
            "1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4", "4:3", "3:4"
        ])
        
        st.subheader("Post-Procesado")
        upscale_option = st.select_slider("Upscaler (Output)", options=["Nativo", "2K", "3K", "4K"])

    # --- SECCION 1: BIBLIOTECA DE REFERENCIAS ---
    st.subheader("Referencia y Contexto")
    col_ref1, col_ref2 = st.columns([1, 2])
    
    with col_ref1:
        uploaded_file = st.file_uploader("Cargar referencia (Materiales/Planos)", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            ref_id = str(uuid.uuid4())[:6]
            img_ref = PIL.Image.open(uploaded_file)
            st.session_state.referencias[ref_id] = {"image": img_ref, "name": uploaded_file.name}
            st.success(f"ID: {ref_id} registrado.")

    with col_ref2:
        if st.session_state.referencias:
            ref_seleccionada = st.multiselect(
                "Seleccionar referencias activas:",
                options=list(st.session_state.referencias.keys()),
                format_func=lambda x: f"{st.session_state.referencias[x]['name']} [{x}]"
            )
        else:
            st.info("Biblioteca de referencias vacia.")

    # --- SECCION 2: GENERACION ---
    st.divider()
    prompt_usuario = st.text_area("Prompt del Proyecto", 
                                 placeholder="Describa el espacio, iluminacion y materiales...")

    if st.button("Ejecutar Generacion"):
        if prompt_usuario:
            with st.status("Generando visualizacion...", expanded=False) as status:
                try:
                    # Mejorador interno silencioso
                    enhancer_res = client.models.generate_content(
                        model="gemini-3-pro-preview",
                        contents=f"Rewrite for professional ArchViz, technical architectural terms, global illumination, raytracing, 8k, photorealistic: {prompt_usuario}"
                    )
                    prompt_final = enhancer_res.text

                    # Preparacion de imagenes de referencia
                    list_images = [st.session_state.referencias[rid]["image"] for rid in ref_seleccionada] if 'ref_seleccionada' in locals() else []

                    # Configuracion de imagen
                    config_gen = types.GenerateImagesConfig(
                        aspect_ratio=aspect_ratio,
                        number_of_images=1
                    )

                    # Ejecucion segun modelo
                    if "imagen-4" in model_map[modelo_nombre]:
                        response = client.models.generate_images(
                            model=model_map[modelo_nombre],
                            prompt=prompt_final,
                            config=config_gen
                        )
                        resultado = response.generated_images[0].image
                    else:
                        response = client.models.generate_content(
                            model=model_map[modelo_nombre],
                            contents=[prompt_final] + list_images,
                            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                        )
                        for part in response.parts:
                            if part.inline_data:
                                resultado = PIL.Image.open(BytesIO(part.inline_data.data))

                    # Guardar en historial (max 5)
                    st.session_state.historial.insert(0, resultado)
                    if len(st.session_state.historial) > 5:
                        st.session_state.historial.pop()

                    status.update(label="Proceso finalizado", state="complete")
                    
                    st.subheader("Resultado Actual")
                    st.image(resultado, use_container_width=True, caption=f"Output: {upscale_option}")

                except Exception as e:
                    st.error(f"Error en el servidor: {e}")
        else:
            st.warning("Ingrese una descripcion.")

    # --- SECCION 3: HISTORIAL RECIENTE ---
    if st.session_state.historial:
        st.divider()
        st.subheader("Historial Reciente (Ultimas 5)")
        cols_hist = st.columns(5)
        for i, img_hist in enumerate(st.session_state.historial):
            with cols_hist[i]:
                st.image(img_hist, use_container_width=True)
                # Opcion de descarga rapida
                buf = BytesIO()
                img_hist.save(buf, format="JPEG")
                st.download_button(f"Descargar #{i+1}", buf.getvalue(), f"render_{i}.jpg", "image/jpeg")
