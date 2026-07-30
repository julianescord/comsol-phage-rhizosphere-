"""
Smoke test de las funciones-tool de server.py, llamandolas directo en
Python (sin pasar por el transporte MCP/stdio). Esto aisla bugs en la
logica de las tools de bugs en el protocolo MCP en si.

Uso: python3 test_server_tools.py
"""

MODEL_TEST = "/home/julianescord/Documentos/COMSOL/test_batch/pesticide_transport_out.mph"

import server as s

print(s.comsol_status())

print(s.open_model("test", MODEL_TEST))

print("Modelos abiertos:", s.list_models())

params = s.list_parameters("test")
print(f"{len(params)} parametros leidos, ejemplo c0={params.get('c0')}")

print("Estudios:", s.list_studies("test"))
print("Datasets:", s.list_datasets("test"))

# Evaluar una expresion simple sobre el dataset ya resuelto (concentracion
# de la especie principal, comp1.c_a, segun vimos en el modelo de referencia).
try:
    result = s.evaluate("test", "comp1.c_a", dataset="Study 2//Solution 2")
    print("evaluate(comp1.c_a) devolvio algo (truncado):", str(result)[:200])
except Exception as exc:
    print(f"evaluate fallo (puede ser el nombre exacto de la expresion/dataset): {exc}")

print(s.close_model("test"))

print("\nSmoke test terminado sin excepciones no controladas.")
