"""
Capa de conexion entre el servidor MCP y COMSOL.

Usa el paquete `mph` (no oficial de COMSOL, PyPI: mph) que controla COMSOL
via su API Java sin necesitar MATLAB. `mph` arranca un proceso motor de
COMSOL localmente y expone un objeto `Model` en Python.

ADVERTENCIA: este modulo no ha sido probado contra una instalacion real
todavia (no se pudo instalar/ejecutar `mph` en esta sesion). El punto mas
incierto es la AUTO-DETECCION de la instalacion de COMSOL: `mph` busca en
rutas tipicas (en Linux, /usr/local/comsol* u /opt/comsol*), y nuestra
instalacion vive en una ruta no estandar
(/media/julianescord/DATA/Programas/comsol64/multiphysics). Si `mph.start()`
falla al no encontrarla, hay dos salidas a probar en orden:

  1. Revisar que devuelve `python3 -c "import mph; print(mph.discovery.backend())"`
     para ver que detecta `mph` realmente.
  2. Si no detecta nada, crear un symlink en una ruta estandar, p.ej.:
     sudo ln -s /media/julianescord/DATA/Programas/comsol64 /usr/local/comsol64
     y reintentar.

No adivines mas alla de esto sin volver a verificar contra la version de
`mph` instalada -- su API de descubrimiento ha cambiado entre versiones.
"""

import threading

COMSOL_ROOT = "/media/julianescord/DATA/Programas/comsol64/multiphysics"

_lock = threading.Lock()
_client = None
_models: dict[str, object] = {}


def get_client():
    """Devuelve el cliente COMSOL (mph.Client), arrancandolo si hace falta.

    Se arranca de forma perezosa (no al importar el modulo) porque iniciar
    el cliente reserva una licencia y tarda varios segundos.
    """
    global _client
    with _lock:
        if _client is None:
            import mph
            _client = mph.start(cores=1)
        return _client


def open_model(alias: str, path: str):
    """Abre un archivo .mph y lo registra bajo un alias corto."""
    client = get_client()
    model = client.load(path)
    _models[alias] = model
    return model


def get_model(alias: str):
    if alias not in _models:
        raise KeyError(
            f"No hay ningun modelo abierto con el alias '{alias}'. "
            f"Modelos abiertos: {list(_models.keys())}"
        )
    return _models[alias]


def list_open_models() -> list[str]:
    return list(_models.keys())


def close_model(alias: str):
    model = _models.pop(alias, None)
    if model is not None:
        client = get_client()
        client.remove(model)
