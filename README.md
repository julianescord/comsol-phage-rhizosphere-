# Modelo FEM de liberación controlada de bacteriófagos en la rizosfera

Modelo de elementos finitos en COMSOL Multiphysics 6.4 de la liberación
controlada de bacteriófagos anti-*Ralstonia solanacearum* desde un vehículo
matricial de alginato hacia la rizosfera, para biocontrol de la marchitez
bacteriana.

La metodología se adapta de Dosmar et al. (2021), *Pharmaceutics* 13(11):1862
(`pharmaceutics-13-01862.pdf`), reemplazando "tejido ocular en capas → vítreo"
por "suelo/rizosfera → superficie radicular".

## Diferencias frente al paper de referencia

El fago no es un fármaco pasivo. El modelo requiere dos términos que la
referencia no contempla:

1. **Inactivación** del fago — sumidero de primer orden.
2. **Replicación** del fago — término *fuente*: al infectar *Ralstonia* en la
   rizosfera el fago se amplifica, convirtiendo el problema en
   reacción-difusión con crecimiento.

## Estructura

```
docs/           Especificación técnica, plan de etapas, datos de fagos
scripts/        Construcción y validación de modelos (fuente de verdad)
models/         Artefactos .mph y salidas — NO versionados, se regeneran
mcp_server/     Servidor MCP que expone COMSOL como herramientas
Markdown/       Paper de referencia convertido a texto
```

Los archivos `.mph` **no se versionan**: son reproducibles ejecutando los
scripts. El código es la fuente de verdad, no el binario.

## Entorno

> El intérprete con `mph` es `mcp_server/venv/bin/python`, **no** el `venv/`
> de la raíz ni el Python del sistema.

```bash
mcp_server/venv/bin/pip install -r mcp_server/requirements.txt
mcp_server/venv/bin/pip install scipy matplotlib   # solo para validación
```

Requiere COMSOL 6.4 instalado (aquí en
`/media/julianescord/DATA/Programas/comsol64/multiphysics`); el paquete `mph`
lo detecta automáticamente vía JPype.

## Plan de etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Difusión pura en suelo homogéneo, validada vs. solución analítica | ✅ validada |
| 2 | D distinto en bead vs. suelo, sorción, inactivación | pendiente |
| 3 | Flujo de agua no saturado (Richards) y advección | pendiente |
| 4 | Sumidero radicular (captación) | pendiente |
| 5 | 3D, múltiples beads, heterogeneidad, calibración | pendiente |

### Etapa 1 — reproducir

```bash
mcp_server/venv/bin/python scripts/build_etapa1.py      # construye el .mph
mcp_server/venv/bin/python scripts/validate_etapa1.py   # resuelve y valida
```

La Etapa 1 se configura deliberadamente para ser **verificable**: con
porosidad = 1 y `TortuosityModel` con τ_F = 1 se cumple De = D y
∂(θc)/∂t = ∂c/∂t, de modo que la interfaz *Transport of Diluted Species in
Porous Media* se reduce exactamente a la 2ª ley de Fick. Eso permite comparar
contra la solución analítica de Crank para una esfera con c₀ uniforme
liberando en un medio infinito, ejercitando la misma interfaz que usarán las
etapas siguientes.

La comparación se hace en **todos los nodos de la malla** vía R = √(r²+z²), lo
que verifica simultáneamente la precisión radial y la simetría esférica.

Resultados de la validación (r_bead = 250 µm, D = 2.2e-12 m²/s, 24 h):

| Métrica | Valor |
|---|---|
| Error máx. FEM vs. analítico | 4.2e-3 · c₀ |
| Error RMS a t = 24 h | 1.2e-4 · c₀ |
| Conservación de masa en el tiempo | exacta |
| Offset absoluto de masa | +0.13 % (discretización del contorno curvo) |

La referencia analítica se autoverifica por conservación de masa antes de
usarse como patrón.

### Nota sobre la escala del vehículo

`r_bead` es un parámetro global. Ojo: en la Etapa 1, con D uniforme y medio
infinito, el problema es **auto-similar** (todo escala con a²/D), así que
barrer `r_bead` solo reescala el eje temporal y no discrimina nada. El barrido
solo aporta información cuando se rompe la auto-similitud — es decir, en la
Etapa 2 en adelante: D_bead ≠ D_suelo, una distancia fija a la raíz, o una
constante de inactivación fija.

## Configuración local

`.env` (no versionado) contiene la clave de API usada por `ai_planner.py`:

```
deepseekk_api_key=...
```
