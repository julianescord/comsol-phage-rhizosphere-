"""
Genera un reporte HTML global a partir de los CSV ya existentes en models/,
delegando la redaccion a un LLM externo (Llama 3.1 70B via API de NVIDIA).

NO ejecuta COMSOL ni simulaciones: es una herramienta de REPORTE, no parte
del pipeline de simulacion (build_*/validate_*/sweep_*/plot_*). Solo lee
numeros ya calculados.

Limitacion importante: el LLM ve unicamente los CSV crudos, sin el contexto
narrativo del proyecto (por que se reordenaron las etapas, que bugs se
encontraron y como, que metrica es fragil y cual robusta). Para el informe
final con esa narrativa se uso en cambio docs/summary/resumen.html, escrito
directamente con el contexto completo de la investigacion. Este script es
mas util para una primera pasada rapida/barata sobre datos nuevos.

Corre con el venv de la RAIZ (necesita openai+python-dotenv), no con
mcp_server/venv:
    venv/bin/python scripts/analisis_datos_deepseek.py
"""
import os
import glob
from openai import OpenAI
from dotenv import load_dotenv

# 1. Cargar la API key desde .env
load_dotenv()
api_key = os.getenv("deepseekk_api_key")

if not api_key:
    print("Error: No se encontró 'deepseekk_api_key' en el archivo .env")
    exit(1)

# 2. Inicializar el cliente de NVIDIA
client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key
)

def generar_reporte_global_html(carpeta_modelos):
    """
    Lee todos los archivos CSV de la carpeta, los concatena y le pide a NVIDIA 
    que genere un reporte HTML global insertando las gráficas PNG correspondientes.
    """
    print(f"Buscando archivos CSV en: {carpeta_modelos}")
    
    archivos_csv = glob.glob(os.path.join(carpeta_modelos, "*.csv"))
    if not archivos_csv:
        print("No se encontraron archivos CSV.")
        return

    datos_completos = ""
    lista_imagenes = []
    
    # Recopilar datos de todos los CSV y encontrar sus PNG asociados
    for ruta_csv in archivos_csv:
        nombre_base = os.path.basename(ruta_csv)
        nombre_sin_ext = os.path.splitext(nombre_base)[0]
        ruta_png = os.path.join(carpeta_modelos, f"{nombre_sin_ext}.png")
        
        imagen_disponible = ""
        if os.path.exists(ruta_png):
            imagen_disponible = f"{nombre_sin_ext}.png"
            lista_imagenes.append(imagen_disponible)
            
        print(f"Leyendo: {nombre_base}")
        try:
            with open(ruta_csv, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            datos_completos += f"\n\n--- ETAPA / ARCHIVO: {nombre_base} ---\n"
            if imagen_disponible:
                datos_completos += f"Grafica correspondiente disponible con el nombre: {imagen_disponible}\n"
            datos_completos += "Datos numéricos:\n"
            datos_completos += contenido
            
        except Exception as e:
            print(f"Error al leer {ruta_csv}: {e}")

    # Definir instrucciones para Llama 3
    prompt_sistema = (
        "Eres un ingeniero experto en simulaciones de COMSOL Multiphysics e investigador científico. "
        "Tu tarea es redactar informes profesionales y exhaustivos estructurados puramente en formato HTML, con diseño CSS elegante."
    )
    
    prompt_usuario = f"""
    A continuación, te presento los resultados numéricos de múltiples etapas de una investigación en COMSOL.
    Quiero que generes un REPORTE GLOBAL en formato HTML completo.
    
    Estructura requerida:
    1. Título y Resumen Ejecutivo.
    2. Metodología general (basada en las variables de los datos).
    3. Análisis por Etapa: Crea una sección para cada archivo CSV proporcionado. En cada etapa:
       - Explica las variables y los resultados de esa etapa.
       - Si en la información de la etapa dice "Grafica correspondiente disponible con el nombre: X.png", DEBES insertar de forma obligatoria una etiqueta HTML de imagen así: <img src="X.png" alt="Gráfica de la etapa X" style="max-width:100%; height:auto;">. 
    4. Discusión General y Conclusiones Finales cruzando datos de las diferentes etapas si es posible.
    
    Importante para el diseño: 
    - El archivo HTML y las imágenes estarán en la misma carpeta, por lo que el atributo src debe llevar solo el nombre de la imagen (ej: src="etapa1_validacion.png").
    - Agrega CSS integrado (<style>) para que se vea moderno, con buena tipografía, márgenes, sombras en las imágenes y colores profesionales.
    - Devuelve ÚNICAMENTE el código HTML crudo. Sin bloques de markdown (```html), sin saludos previos ni explicaciones al final.
    
    Aquí están todos los datos:
    {datos_completos}
    """

    print("\nTodos los datos cargados. Enviando todo el paquete a la API de NVIDIA (Llama 3.1 70B)...")
    print("Esto puede tardar unos minutos ya que es un reporte global exhaustivo.")
    
    try:
        completion = client.chat.completions.create(
          model="meta/llama-3.1-70b-instruct", 
          messages=[
              {"role": "system", "content": prompt_sistema},
              {"role": "user", "content": prompt_usuario}
          ],
          temperature=0.2, # Baja temperatura para análisis preciso
          max_tokens=4000, 
          stream=False,
          timeout=400 # 6+ minutos de timeout para darle tiempo holgado a NVIDIA
        )
        
        reporte_html = completion.choices[0].message.content
        
        archivo_salida = os.path.join(carpeta_modelos, "reporte_global_resultados.html")
        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(reporte_html)
            
        print(f"\n¡Éxito total! El reporte integral se ha generado y guardado en: {archivo_salida}")
        print("Ábrelo en tu navegador para ver el análisis de todas las etapas con sus respectivas gráficas.")
        
    except Exception as e:
        print(f"\nOcurrió un error al contactar con la API o guardar el archivo: {e}")

if __name__ == "__main__":
    carpeta_modelos = "models"
    generar_reporte_global_html(carpeta_modelos)
