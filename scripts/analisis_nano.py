"""
Analisis (NO simulado) de la escala nanometrica del vehiculo de alginato.

La escala nano (~100 nm) NUNCA se corrio en COMSOL, a diferencia de la
escala micrometrica (25-1000 um) que si tiene barridos FEM reales en
sweep_etapa2.py y siguientes. Se descarto sin simular por dos razones:
  1. Fisica: el vehiculo debe ser mayor que la carga; los fagos jumbo
     anti-Ralstonia miden ~250-290 nm, no caben en una nanoesfera de 100 nm.
  2. Numerica/trivial: el tiempo caracteristico a^2/D para a=100 nm es de
     milisegundos (liberacion practicamente instantanea) -- no hay nada que
     un solver FEM aporte sobre un calculo analitico tan simple.

Este script calcula esos tiempos analiticamente (formula cerrada, sin FEM) y
delega a un LLM externo (Llama 3.1 70B via API de NVIDIA) solo la REDACCION
de la seccion de discusion correspondiente. Es una herramienta de reporte,
no parte del pipeline de simulacion.

Corre con el venv de la RAIZ (necesita openai+python-dotenv):
    venv/bin/python scripts/analisis_nano.py
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("deepseekk_api_key")

if not api_key:
    print("Error: No se encontró la API key en .env")
    exit(1)

client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key
)

def analizar_escala_nano():
    """
    Calcula el tiempo característico de liberación para escalas nanométricas
    usando la fórmula analítica (ya que FEM en COMSOL no era práctico)
    y usa NVIDIA NIM para generar el texto de análisis faltante.
    """
    print("Calculando tiempos de liberación para escala nano...")
    
    # Difusividad del fago en agua (tomada de la metodología)
    D_water = 2.2e-12 
    
    # Radios nanométricos a evaluar (en metros)
    radios_nano_nm = [50, 100, 200, 500, 1000] # de 50nm a 1 micra
    
    resultados_csv = "radio_nm,tiempo_caracteristico_s,comentario\n"
    
    for r_nm in radios_nano_nm:
        a_m = r_nm * 1e-9
        # Tiempo característico de difusión t = a^2 / D
        tau_s = (a_m**2) / D_water
        
        # Clasificar la utilidad
        if tau_s < 1:
            comentario = "Liberación instantánea (milisegundos)"
        elif tau_s < 60:
            comentario = "Liberación rapidísima (segundos)"
        else:
            comentario = "Liberación muy rápida (minutos)"
            
        resultados_csv += f"{r_nm},{tau_s:.6e},{comentario}\n"
        print(f"Radio: {r_nm} nm -> Tiempo de liberación: {tau_s:.4f} s")

    prompt_sistema = (
        "Eres un ingeniero experto en simulaciones de COMSOL y dinámica de fluidos. "
        "Estás completando un reporte científico y tu tarea es escribir una sección muy técnica en HTML."
    )
    
    prompt_usuario = f"""
    Estoy completando un reporte técnico sobre la liberación controlada de bacteriófagos desde una microesfera de alginato.
    Claude generó el reporte para la escala micrométrica (25 a 1000 micras), pero omitió el análisis para la escala nanométrica.
    
    He calculado analíticamente los tiempos de liberación (tau = a^2 / D) para esferas nanométricas, asumiendo D = 2.2e-12 m2/s.
    Aquí están los resultados:
    
    {resultados_csv}
    
    Además, ten en cuenta esta restricción física vital: los bacteriófagos jumbo miden aproximadamente 250 nm, por lo que una nanoesfera de 100 nm es físicamente imposible (el vehículo debe ser más grande que la carga). Solo un podovirus muy pequeño (~70 nm) podría caber al límite. E incluso si cabe, el tiempo de liberación es de milisegundos.
    
    Tarea: Escribe la sección HTML completa llamada "Análisis de la Escala Nanométrica (Casos Límite)".
    Esta sección será inyectada en el reporte principal. 
    1. Debe usar etiquetas HTML limpias (<h3>, <p>, <ul>).
    2. Debe analizar matemáticamente por qué la escala nano resulta en una "liberación flash" (milisegundos a segundos) y no sirve para la liberación prolongada que buscamos (14-21 días).
    3. Debe mencionar la restricción física del tamaño del fago vs el vehículo.
    4. Devuelve ÚNICAMENTE el código HTML, sin markdown ni introducciones.
    """

    print("\nEnviando datos a la API de NVIDIA (Llama 3.1 70B)...")
    try:
        completion = client.chat.completions.create(
          model="meta/llama-3.1-70b-instruct",
          messages=[
              {"role": "system", "content": prompt_sistema},
              {"role": "user", "content": prompt_usuario}
          ],
          temperature=0.2,
          max_tokens=1500,
          stream=False,
          timeout=120
        )
        
        html_nano = completion.choices[0].message.content
        
        archivo_salida = "models/analisis_nano.html"
        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(html_nano)
            
        print(f"\n¡Éxito! El análisis de la escala nano se ha guardado en: {archivo_salida}")
        print("Ahora puedes darle este archivo a Claude para que lo integre en el reporte final.")
        
    except Exception as e:
        print(f"Error al conectar con la API: {e}")

if __name__ == "__main__":
    analizar_escala_nano()
