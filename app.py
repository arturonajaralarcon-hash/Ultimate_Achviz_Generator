import streamlit as st
from google import genai
from google.genai import types # Para configuraciones avanzadas
import PIL.Image
import io

# Configuración visual
st.set_page_config(page_title="Gemini 3 Image Hub", page_icon="🍌", layout="centered")

# --- SEGURIDAD ---
PASSWORD_CORRECTA = "amigo2026" # Cámbiala por la que quieras

st.sidebar.title("🔐 Acceso Privado")
password = st.sidebar.text_input("Contraseña:", type="password")

if password == PASSWORD_CORRECTA:
    # Inicializamos el cliente con tu API Key de los Secrets de Streamlit
    # La sintaxis: client = genai.Client(api_key="...")
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

    st.title("🎨 Gemini 3 & Imagen 4 Studio")
    st.markdown("Genera imágenes usando mis tokens de forma segura.")

    # --- SELECTOR DE MODELOS (Mapeo de nombres a IDs reales del API) ---
    # Nota: Los modelos de imagen usan 'generate_images', los de texto 'generate_content'
    model_map = {
        "Imagen 4 Ultra Generate": "imagen-4-ultra",
        "Imagen 4 Generate": "imagen-4",
        "Nano Banana Pro (Gemini 3 Pro Image)": "gemini-3-pro-vision-image-001",
        "Nano Banana (Gemini 2.5 Flash Preview Image)": "gemini-2.5-flash-image-preview"
    }

    with st.sidebar:
        st.header("Parámetros")
        seleccion = st.selectbox("Modelo de imagen:", list(model_map.keys()))
        modelo_id = model_map[seleccion]
        
        # Opción extra para Gemini 3 Pro (Texto)
        usar_mejorador = st.checkbox("Mejorar prompt con Gemini 3 Pro", value=True)

    prompt_usuario = st.text_area("¿Qué tienes en mente?", placeholder="Ej: Un gato cyber-banana volando sobre Saturno...")

    if st.button("Generar Imagen 🚀"):
        if prompt_usuario:
            with st.spinner(f"Invocando a {seleccion}..."):
                try:
                    # 1. (Opcional) Usamos Gemini 3 Pro para expandir el prompt (Sintaxis exacta que pediste)
                    final_prompt = prompt_usuario
                    if usar_mejorador:
                        # Sintaxis solicitada: client.models.generate_content
                        res_text = client.models.generate_content(
                            model="gemini-3-pro",
                            contents=f"Mejora este prompt para un generador de imágenes, sé descriptivo: {prompt_usuario}",
                        )
                        final_prompt = res_text.text
                        st.caption(f"**Prompt optimizado:** {final_prompt}")

                    # 2. Generación de Imagen
                    # Usamos la sintaxis del SDK para Imagen
                    response = client.models.generate_images(
                        model=modelo_id,
                        prompt=final_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            include_rai_reason=True
                        )
                    )

                    # 3. Mostrar resultado
                    # En el SDK actual, las imágenes vienen en bytes o objetos PIL
                    for output in response.generated_images:
                        st.image(output.image, caption=f"Resultado: {seleccion}")
                        
                    st.balloons()

                except Exception as e:
                    st.error(f"Error detectado: {e}")
                    st.info("Tip: Verifica que tu API Key tenga permisos para los modelos Imagen 4.")
        else:
            st.warning("Escribe algo para empezar.")
else:
    if password:
        st.error("Clave incorrecta. Pídele acceso al dueño de los tokens.")
    st.info("Bienvenido. Introduce la clave en el panel lateral.")
