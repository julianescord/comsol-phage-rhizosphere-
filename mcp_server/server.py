"""
Servidor MCP para controlar COMSOL Multiphysics desde Claude Code (u otro
cliente MCP) sin necesitar MATLAB, usando el paquete `mph` sobre la API
Java de COMSOL.

ADVERTENCIA: esqueleto sin probar contra una instalacion real de `mph`/MCP
en esta sesion (ver notas de verificacion en comsol_bridge.py y README.md).
Antes de confiar en el, correr diagnose.py y probar cada herramienta con
un modelo pequeno (p.ej. el pesticide_transport_out.mph que ya generamos).
"""

from mcp.server.fastmcp import FastMCP

import comsol_bridge as bridge

mcp = FastMCP("comsol")


@mcp.tool()
def comsol_status() -> str:
    """Verifica que el cliente COMSOL este arrancado y devuelve su version."""
    client = bridge.get_client()
    return f"Cliente COMSOL activo. Version: {client.version}"


@mcp.tool()
def open_model(alias: str, path: str) -> str:
    """Abre un archivo .mph y lo registra bajo un alias corto para referenciarlo
    en las demas herramientas. Ejemplo: alias='rizosfera', path='/ruta/modelo.mph'."""
    bridge.open_model(alias, path)
    return f"Modelo '{alias}' abierto desde {path}"


@mcp.tool()
def list_models() -> list[str]:
    """Lista los alias de los modelos actualmente abiertos en esta sesion."""
    return bridge.list_open_models()


@mcp.tool()
def list_parameters(alias: str) -> dict[str, str]:
    """Devuelve todos los parametros globales definidos en el modelo."""
    model = bridge.get_model(alias)
    return dict(model.parameters())


@mcp.tool()
def set_parameter(alias: str, name: str, value: str) -> str:
    """Cambia el valor de un parametro global del modelo, p.ej.
    set_parameter('rizosfera', 'D_soil', '2e-10[m^2/s]')."""
    model = bridge.get_model(alias)
    model.parameter(name, value)
    return f"{name} = {value}"


@mcp.tool()
def list_studies(alias: str) -> list[str]:
    """Lista los estudios (Study nodes) definidos en el modelo."""
    model = bridge.get_model(alias)
    return list(model.studies())


@mcp.tool()
def run_study(alias: str, study: str | None = None) -> str:
    """Resuelve un estudio del modelo. Si no se especifica 'study', resuelve
    todos los estudios definidos. Puede tardar segundos a minutos segun el
    tamano del modelo."""
    model = bridge.get_model(alias)
    if study:
        model.solve(study)
        return f"Estudio '{study}' resuelto."
    model.solve()
    return "Todos los estudios resueltos."


@mcp.tool()
def list_datasets(alias: str) -> list[str]:
    """Lista los datasets de resultados disponibles tras resolver el modelo."""
    model = bridge.get_model(alias)
    return list(model.datasets())


@mcp.tool()
def evaluate(alias: str, expression: str, dataset: str | None = None) -> str:
    """Evalua una expresion de resultados (p.ej. 'c', 'p', 'comp1.c_a') sobre
    un dataset dado y devuelve los valores como texto. Util para leer
    concentracion en un punto/frontera especifica (p.ej. superficie
    radicular) una vez resuelto el estudio."""
    model = bridge.get_model(alias)
    kwargs = {"dataset": dataset} if dataset else {}
    values = model.evaluate(expression, **kwargs)
    return str(values)


@mcp.tool()
def list_exports(alias: str) -> list[str]:
    """Lista los nodos de exportacion (Export) preconfigurados en el modelo."""
    model = bridge.get_model(alias)
    return list(model.exports())


@mcp.tool()
def export_data(alias: str, node: str, filepath: str) -> str:
    """Ejecuta un nodo de exportacion existente y escribe el resultado en
    filepath (CSV, imagen, etc. segun como este configurado el nodo)."""
    model = bridge.get_model(alias)
    model.export(node, filepath)
    return f"Exportado '{node}' a {filepath}"


@mcp.tool()
def save_model(alias: str, path: str | None = None) -> str:
    """Guarda el modelo. Si no se da path, sobrescribe el archivo original."""
    model = bridge.get_model(alias)
    if path:
        model.save(path)
        return f"Guardado en {path}"
    model.save()
    return "Guardado en el archivo original."


@mcp.tool()
def close_model(alias: str) -> str:
    """Cierra un modelo y libera su memoria en el motor de COMSOL."""
    bridge.close_model(alias)
    return f"Modelo '{alias}' cerrado."


if __name__ == "__main__":
    mcp.run(transport="stdio")
