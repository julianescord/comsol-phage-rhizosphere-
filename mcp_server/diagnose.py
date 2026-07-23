"""
Script de diagnostico paso a paso. Correr esto ANTES de intentar usar
server.py, para aislar en cual capa falla algo si algo falla (deteccion de
COMSOL, arranque del cliente, carga de modelo, evaluacion de resultados).

Uso:
    python3 diagnose.py

Cada paso imprime OK o el error puntual y se detiene ahi -- no sigue a
paso siguiente si uno falla, para no generar tracebacks confusos en
cascada.
"""

import sys

MODEL_TEST = "/home/julianescord/Documentos/COMSOL/test_batch/pesticide_transport_out.mph"


def step(name):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            print(f"\n--- {name} ---")
            try:
                result = fn(*args, **kwargs)
                print("OK")
                return result
            except Exception as exc:
                print(f"FALLO: {type(exc).__name__}: {exc}")
                sys.exit(1)
        return wrapper
    return decorator


@step("1. Importar mph")
def import_mph():
    import mph
    print(f"mph version: {getattr(mph, '__version__', 'desconocida')}")
    return mph


@step("2. Deteccion de instalacion COMSOL")
def check_discovery(mph):
    # Nombre exacto del submodulo/funcion de descubrimiento a confirmar
    # contra la version instalada -- si esto falla, es la primera pista.
    info = mph.discovery.backend()
    print(info)
    return info


@step("3. Arrancar cliente COMSOL (reserva una licencia)")
def start_client(mph):
    client = mph.start(cores=1)
    print(f"Version motor COMSOL: {client.version}")
    return client


@step("4. Cargar modelo de prueba ya resuelto")
def load_model(client):
    model = client.load(MODEL_TEST)
    print(f"Modelo cargado: {model.name()}")
    return model


@step("5. Leer parametros y estudios del modelo")
def inspect_model(model):
    print("Parametros:", dict(model.parameters()))
    print("Estudios:", list(model.studies()))
    print("Datasets:", list(model.datasets()))


if __name__ == "__main__":
    mph = import_mph()
    check_discovery(mph)
    client = start_client(mph)
    model = load_model(client)
    inspect_model(model)
    print("\nTodo funcionando. Ya se puede probar server.py.")
