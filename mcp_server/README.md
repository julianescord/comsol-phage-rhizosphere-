# Servidor MCP para COMSOL

Expone COMSOL Multiphysics como herramientas MCP (`open_model`, `set_parameter`,
`run_study`, `evaluate`, `export_data`, `save_model`, ...) para poder pedirle
directamente a Claude Code cosas como *"corre el estudio y dime la
concentración en la superficie radicular"*, sin pasar por la GUI ni escribir
scripts sueltos cada vez.

**Estado: esqueleto sin probar.** Se escribió sin poder ejecutar Python en
esta sesión (bloqueos del clasificador de seguridad). Antes de usarlo en
serio, hay que validarlo capa por capa — para eso está `diagnose.py`.

## Arquitectura

```
Claude Code (MCP client)
        │  stdio
        ▼
server.py (FastMCP, expone las tools)
        │
        ▼
comsol_bridge.py (maneja el cliente mph y los modelos abiertos)
        │
        ▼
mph (paquete de Python, no oficial de COMSOL, via JPype)
        │
        ▼
API Java de COMSOL 6.4 (confirmada presente en la instalación)
```

## 1. Instalar dependencias

```bash
cd /home/julianescord/Documentos/COMSOL/mcp_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Correr el diagnóstico ANTES de tocar el servidor MCP

```bash
python3 diagnose.py
```

Este script prueba, en orden, y se detiene en el primer fallo:
1. Que `mph` se importe.
2. Que `mph` **detecte** la instalación de COMSOL — este es el paso más
   incierto, porque nuestra instalación está en una ruta no estándar
   (`/media/julianescord/DATA/Programas/comsol64/multiphysics`) y `mph`
   normalmente escanea rutas típicas.
3. Que el cliente arranque (esto reserva una licencia — **cerrar COMSOL
   Desktop antes** si está abierto, para evitar conflictos de licencia).
4. Que cargue el modelo `pesticide_transport_out.mph` que ya generamos y
   validamos con `comsol batch`.
5. Que se puedan leer sus parámetros/estudios/datasets.

**Si el paso 2 falla** (no detecta la instalación), probar:

```bash
sudo ln -s /media/julianescord/DATA/Programas/comsol64 /usr/local/comsol64
```

y volver a correr `diagnose.py`. Si sigue sin detectarla, hay que revisar
el código fuente de `mph/discovery.py` de la versión instalada para ver
qué rutas escanea exactamente — pégame el error y lo resolvemos juntos en
vez de seguir adivinando.

## 3. Probar el servidor manualmente (opcional pero recomendado)

Antes de conectarlo a Claude Code, se puede probar con el inspector oficial
de MCP:

```bash
npx @modelcontextprotocol/inspector python3 server.py
```

Esto abre una UI web donde se puede invocar cada tool a mano y ver la
respuesta cruda, sin depender de que un cliente MCP las interprete bien.

## 4. Registrar el servidor en Claude Code

Opción A — CLI:

```bash
claude mcp add comsol -- python3 /home/julianescord/Documentos/COMSOL/mcp_server/server.py
```

Opción B — archivo `.mcp.json` en la raíz del proyecto:

```json
{
  "mcpServers": {
    "comsol": {
      "command": "python3",
      "args": ["/home/julianescord/Documentos/COMSOL/mcp_server/server.py"]
    }
  }
}
```

Si usaste el venv, el `command` debe apuntar al Python del venv
(`/home/julianescord/Documentos/COMSOL/mcp_server/venv/bin/python3`), no al
del sistema — si no, no vas a tener `mph` ni `mcp` instalados ahí.

## Notas

- Solo se arranca el cliente COMSOL (y se reserva la licencia) la primera
  vez que se llama a alguna tool — abrir el servidor no consume licencia
  por sí solo.
- Un solo proceso motor sirve para todos los modelos que se abran en la
  misma sesión (identificados por `alias`).
- Las herramientas cubren el flujo básico (abrir, parametrizar, resolver,
  evaluar, exportar, guardar). Si hace falta algo que no está expuesto
  (crear geometría desde cero, añadir físicas nuevas, etc.), se accede al
  objeto Java crudo vía `model.java` dentro de `comsol_bridge.py` y se
  agrega como tool nueva.
