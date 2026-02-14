import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
from io import BytesIO

# Configuración de página
st.set_page_config(page_title="Gemini & Imagen Studio 2026", page_icon="🍌")

# --- SEGURIDAD ---
PASSWORD_CORRECTA = "amigo2026"
st.sidebar.title("🔐 Acceso")
password = st.sidebar.text_input("Contraseña:", type="password")

if password == PASSWORD_CORRECTA:
    # Usamos la sintaxis oficial: client = genai.Client(api_key=...)
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    st.title("🎨 Laboratorio de Imágenes")
    
    # --- MAPEADO DE MODELOS 2026 ---
    # Nota: Los modelos "Nano Banana" son versiones de Gemini especializadas en imagen.
    model_options = {
        "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-image-preview",
        "Nano Banana (Gemini 2.5 Flash Preview Image)": "gemini-2.5-flash-image",
        "Imagen 4 Ultra Generate": "imagen-4.0-ultra-generate-001",
        "Imagen 4 Generate": "imagen-4.0-generate-001"
    }

    modelo_nombre = st.sidebar.selectbox("Elige tu modelo:", list(model_options.keys()))
    modelo_id = model_options[modelo_nombre]

    st.sidebar.divider()
    usar_mejorador = st.sidebar.checkbox("Optimizar con Gemini 3 Pro (Texto)", value=True)

    prompt_original = st.text_area("Describe tu imagen:", placeholder="Un astronauta de cristal...")

    if st.button("Generar ✨"):
        if prompt_original:
            with st.spinner(f"Procesando con {modelo_nombre}..."):
                try:
                    final_prompt = prompt_original

                    # 1. MEJORADOR (Sintaxis exacta: client.models.generate_content)
                    if usar_mejorador:
                        # Corregido: gemini-3-pro-preview es el ID correcto en v1beta
                        res_text = client.models.generate_content(
                            model="gemini-3-pro-preview",
                            contents=f"Embellece este prompt para generar una imagen artística: {prompt_original}"
                        )
                        final_prompt = res_text.text
                        st.caption(f"**Prompt mejorado:** {final_prompt}")

                    # 2. GENERACIÓN DE IMAGEN
                    # Los modelos Imagen 4 usan 'generate_images'
                    if "imagen-4" in modelo_id:
                        response = client.models.generate_images(
                            model=modelo_id,
                            prompt=final_prompt,
                            config=types.GenerateImagesConfig(number_of_images=1)
                        )
                        for img_obj in response.generated_images:
                            st.image(img_obj.image, caption=modelo_nombre)
                    
                    # Los modelos Gemini (Nano Banana) usan 'generate_content' con modalidad imagen
                    else:
                        response = client.models.generate_content(
                            model=modelo_id,
                            contents=final_prompt,
                            config=types.GenerateContentConfig(
                                response_modalities=["IMAGE"]
                            )
                        )
                        # Extraer la imagen de las partes de la respuesta
                        for part in response.parts:
                            if part.inline_data:
                                # Convertir bytes a imagen PIL
                                img = PIL.Image.open(BytesIO(part.inline_data.data))
                                st.image(img, caption=modelo_nombre)

                    st.success("¡Listo!")
                    st.balloons()

                except Exception as e:
                    st.error(f"Error de API: {e}")
                    st.info("Asegúrate de que tu API Key tenga habilitado el acceso a 'Vertex AI' o 'Imagen API' en Google Cloud Console.")
        else:
            st.warning("Escribe algo primero.")
else:
    st.info("Introduce la clave para activar el generador.")
