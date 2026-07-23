import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Obtener la API key (asegúrate de que el nombre coincida exactamente con el de tu .env)
api_key = os.getenv("deepseekk_api_key")

if not api_key:
    print("Error: No se encontró 'deepseekk_api_key' en el archivo .env")
    exit(1)

client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key
)

print("Enviando petición a NVIDIA NIM...")
completion = client.chat.completions.create(
  model="deepseek-ai/deepseek-v4-pro",
  messages=[{"role":"user", "content":"Hola, esto es una prueba de conexión. ¿Puedes responder brevemente?"}],
  temperature=1,
  top_p=0.95,
  max_tokens=16384,
  extra_body={"chat_template_kwargs":{"thinking":False}},
  stream=False
)

print("\nRespuesta de DeepSeek:")
print(completion.choices[0].message.content)
