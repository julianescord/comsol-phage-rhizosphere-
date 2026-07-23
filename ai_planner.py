import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
api_key = os.getenv("deepseekk_api_key")

if not api_key:
    print("Error: No se encontró 'deepseekk_api_key' en el archivo .env")
    exit(1)

# Inicializar el cliente
client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key
)

def leer_archivo(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error al leer {ruta}: {e}")
        return ""

print("Leyendo documentación del proyecto...")
# Leemos el contenido de tus dos archivos Markdown
especificacion = leer_archivo("docs/especificacion_tecnica.md")
ruta_aprendizaje = leer_archivo("docs/ruta_aprendizaje.md")

# Definimos el comportamiento de la IA
prompt_sistema = (
    "Eres un ingeniero experto en simulaciones FEM y COMSOL Multiphysics, especializado "
    "en transporte de especies químicas y medios porosos. Tu objetivo es ayudar a planificar "
    "y ejecutar proyectos de ingeniería."
)

# Construimos el mensaje con el contexto de tus documentos
prompt_usuario = f"""
Estoy trabajando en un modelo FEM de liberación controlada en la rizosfera usando COMSOL.

Aquí tienes la Especificación Técnica de mi proyecto:
---
{especificacion}
---

Y aquí está mi Ruta de Aprendizaje/Plan de Acción:
---
{ruta_aprendizaje}
---

Basándote en estos dos documentos, por favor:
1. Identifica en qué punto del proyecto me encuentro (cuál es el siguiente paso lógico).
2. Dame instrucciones técnicas detalladas y prácticas sobre cómo ejecutar ese siguiente paso en COMSOL.
3. Si hay parámetros críticos o condiciones de frontera que deba tener en cuenta para esta etapa, lístalos.
"""

print("Consultando a DeepSeek (NIM). Analizando el proyecto, esto puede tardar un momento...")

completion = client.chat.completions.create(
  model="deepseek-ai/deepseek-v4-pro",
  messages=[
      {"role": "system", "content": prompt_sistema},
      {"role": "user", "content": prompt_usuario}
  ],
  temperature=0.4,
  max_tokens=4000,
  stream=False
)

respuesta = completion.choices[0].message.content

# Guardamos el resultado en un nuevo documento de planificación
archivo_salida = "docs/plan_siguientes_pasos_ai.md"
os.makedirs("docs", exist_ok=True)
with open(archivo_salida, "w", encoding="utf-8") as f:
    f.write(respuesta)

print(f"\n¡Análisis completado exitosamente! El plan de acción sugerido por la IA se ha guardado en: {archivo_salida}")
