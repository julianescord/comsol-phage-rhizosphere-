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
| 2 | D_bead ≠ D_suelo, porosidad real (Millington-Quirk), inactivación | ✅ verificada |
| 3 | Captación radicular saturable (sumidero Michaelis-Menten) | ✅ verificada |
| R | **Replicación del fago: infección fago–Ralstonia (Lotka-Volterra)** | ✅ verificada |
| 4 | Flujo de agua no saturado (Richards) y advección | pendiente |
| 5 | 3D, múltiples beads, heterogeneidad, calibración | pendiente |

> **Reordenamiento:** la captación radicular (Etapa 4 en el plan original) se
> adelantó a la 3ª posición, y el flujo de agua pasó a la 4ª. Motivo: el
> barrido de la Etapa 2 mostró que sin un sumidero que premie la
> sostenibilidad la entrega es monótona; la raíz es el proceso que puede crear
> ese óptimo, así que es la pregunta prioritaria. Luego se saltó a la
> **replicación** (etapa R), el aporte de novedad del proyecto y lo único que
> podía invertir la conclusión monótona — y lo hace.

## Hallazgo central del proyecto (hasta ahora)

Con el fago como agente **pasivo** (difunde, se inactiva, es captado — Etapas
2 y 3), el diseño óptimo del vehículo es siempre el mismo: **lo más pequeño y
difusivo posible**, cerca de la raíz. La entrega es monótona, no hay argumento
de modelado para beads grandes de liberación sostenida.

Cuando el fago **se replica** al infectar a *Ralstonia* (etapa R), la
recomendación **se invierte**: la métrica biológicamente relevante — la carga
acumulada de patógeno en el tiempo — favorece la **liberación sostenida**
(beads grandes, gel de difusión lenta). El mecanismo es un ciclo
depredador-presa con retardo: un pulso rápido de fago aplasta a *Ralstonia*
una vez y se agota, tras lo cual el patógeno rebrota; la liberación sostenida
mantiene la presión del fago sobre ese rebrote. Esto da, por primera vez en el
proyecto, un argumento cuantitativo a favor de las micro-beads de liberación
sostenida.

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

### Etapa 2 — reproducir

```bash
mcp_server/venv/bin/python scripts/build_etapa2.py       # modelo realista
mcp_server/venv/bin/python scripts/validate_etapa2.py    # Checks A y B
mcp_server/venv/bin/python scripts/sweep_etapa2.py       # barrido
mcp_server/venv/bin/python scripts/plot_etapa2.py        # figura
```

Añade sobre la Etapa 1: difusividad propia dentro de la bead, porosidad real
del suelo con difusividad efectiva de Millington-Quirk, e inactivación del
fago como sumidero de primer orden.

**No incluye sorción de equilibrio (K_d lineal), y es una decisión física, no
una omisión.** La isoterma de equilibrio es un concepto de *soluto*; un fago
de ~200 nm es un **coloide**, y su retención en suelo es adhesión/filtración
coloidal — cinética y poco reversible. Se modela como sumidero cinético
adicional (`k_att`, desactivado por defecto), no como reparto instantáneo.

#### Verificación por partes

Cada término nuevo se verifica por separado llevando el modelo a una
configuración degenerada con solución exacta (`--uniform-medium`):

| Check | Configuración | Solución exacta | Resultado |
|---|---|---|---|
| A — inactivación | medio uniforme, τ=1, ε=0.45, k>0 | Crank·exp(−k·t) | error 4.2e-3·c₀ |
| B — Millington-Quirk | medio uniforme, k=0, ε=0.45, MQ | Crank con D_app | error 4.3e-3·c₀ |

Los dos checks resolvieron **empíricamente** convenciones de COMSOL que no
conviene asumir:

- **`ReactingVolumeType`.** Su valor por defecto es `TotalVolume`, que
  interpreta `R_c` por volumen total; como la ecuación es
  ε·∂c/∂t = ∇·(D_e∇c) + R_c, eso habría dado una tasa efectiva de k/ε en vez
  de k. Con `PoreVolume` el Check A confirma que k_ef = k_inact (las
  alternativas k/ε y k·ε dan errores 4–5× mayores).
- **Difusividad efectiva.** El Check B identifica D_app = ε^(1/3)·D_w — es
  decir D_e = ε^(4/3)·D — que es Millington-Quirk saturado. El ajuste libre
  da el exponente 0.342 frente al 1/3 teórico.

En el Check A el error del ganador (4.247e-3) coincide con el error de
discretización ya caracterizado en la Etapa 1 (4.228e-3): el término de
reacción no introduce error propio.

#### Hallazgo del barrido r_bead × D_bead

`sweep_etapa2.py` barre 4 radios × 4 difusividades midiendo la fracción de la
dosis que llega **activa** al suelo (`etapa2_barrido.png`). Resultado, que
**contradice la hipótesis inicial** de un óptimo intermedio: con la
inactivación como único sumidero la entrega es **monótona** — la bead más
pequeña y el gel más abierto siempre entregan más (95 % en 25 µm/D_agua; 5 %
en 1000 µm/2.2e-15 m²/s).

La razón es asimétrica: la liberación lenta **sí** se penaliza (el fago se
inactiva dentro de la bead antes de salir; para 1000 µm/2.2e-15,
τ_dif = a²/D ≈ 5000 d ≫ los 14 d simulados), pero la liberación rápida **no**,
porque una vez en el suelo el fago decae al mismo ritmo k. El compromiso que
premiaría una liberación sostenida solo aparece cuando se añade un proceso que
la aproveche — captación radicular (Etapa 4) o replicación con umbral
(Etapa 5). Hasta entonces, el diseño óptimo es el vehículo más pequeño y
difusivo posible.

### Etapa 3 (raíz) — reproducir

```bash
mcp_server/venv/bin/python scripts/build_raiz.py       # modelo con raíz
mcp_server/venv/bin/python scripts/validate_raiz.py    # balance de masa
mcp_server/venv/bin/python scripts/sweep_raiz.py       # barrido
mcp_server/venv/bin/python scripts/plot_raiz.py        # figura
```

Añade una **captación radicular saturable** (Michaelis-Menten) como sumidero
en la frontera exterior, a distancia L de la bead:

```
J_root = -Vmax_root · c / (Km_root + c)      [mol/(m²·s)]
```

Saturable a propósito: es el mecanismo candidato para romper la monotonía de
la Etapa 2. Un pulso rápido satura la captación (c ≫ Km) y el exceso se
inactiva; un flujo sostenido se mantiene cerca de Km y la raíz lo capta con
eficiencia. `r_dom` deja de ser "medio infinito" y pasa a ser **L, la
distancia bead–raíz**, un parámetro físico. La frontera exterior se aísla con
una `Difference` de dos selecciones `Ball`.

#### Verificación por balance de masa de 4 términos

Esta geometría (bead esférica + sumidero MM en la frontera) no tiene solución
analítica cerrada. Se verifica con un invariante exacto — en todo instante,
`M₀ = activo(t) + captado(t) + inactivado(t)`. Las masas acumuladas
(captada e inactivada) se integran **dentro de COMSOL** con dos ODEs globales
(`GlobalEquations`), no por trapecio post-hoc, así que el solver las cierra a
alta precisión.

| Comprobación | Resultado |
|---|---|
| Deriva del balance (caso base y límite) | 2.1e-5 relativo a la dosis |
| Límite Vmax→0 (debe reproducir la Etapa 2) | captado 0.000 % |
| Offset de CI (artefacto, ver abajo) | −2.2 % |

Dos hallazgos de la verificación:

- **Bug encontrado por el balance.** El nodo `FluxBoundary` trae `species = 0`
  por defecto y sin `species = 1` **la BC no se aplica a la especie** — el
  sumidero no removía masa. Se detectó porque el balance daba lo imposible:
  `inactivado` alcanzaba toda la dosis y *además* había masa captada.
- **Offset de condición inicial.** La CI discontinua (c₀ en la bead, 0 fuera)
  se proyecta sobre la malla y el solver la suaviza, así que la dosis
  realmente cargada es `M_active(0) ≈ 0.978·M₀`. Es un artefacto de malla, no
  de física; todas las fracciones se refieren a la dosis real cargada.

#### Longitud de penetración: la bead debe estar cerca de la raíz

El fago difunde hacia la raíz mientras se inactiva. La escala natural es la
**longitud de penetración** √(D_suelo/k_inact) ≈ **0.36 mm** (con los
placeholders actuales). La fracción captada colapsa cuando L la supera:

| L [mm] | 0.3 | 0.5 | 1.0 | 2.0 | 5.0 |
|---|---|---|---|---|---|
| f captada | 51 % | 46 % | 31 % | 9 % | 0.09 % |

Implicación de diseño: **la bead tiene que estar sub-milimétricamente cerca de
la superficie radicular** para que el fago llegue vivo. Por eso el barrido del
óptimo se corre a L = 0.5 mm, no a los 5 mm del caso base.

#### ¿La raíz crea el óptimo interior? — No

El barrido r_bead × D_bead a L = 0.5 mm con captación saturable
(`raiz_barrido.png`) responde la pregunta que motivó adelantar esta etapa: la
fracción captada por la raíz **sigue siendo monótona**, con el máximo en la
esquina (bead más pequeña y difusiva, 87 %). La captación saturable **no**
rompe la monotonía de la Etapa 2.

La razón: la ventaja de liberar rápido (el fago escapa de la bead antes de
inactivarse dentro) domina sobre la penalización por saturación de la
captación. Un pulso rápido satura la raíz y desperdicia algo, pero ese
desperdicio es menor que la pérdida por inactivación intra-bead de una
liberación lenta.

**Conclusión de diseño acumulada (Etapas 2 + 3):** con inactivación y
captación radicular saturable como procesos, el vehículo óptimo es el más
pequeño y difusivo posible, colocado a menos de ~1 longitud de penetración de
la raíz. No hay ningún argumento de modelado para beads grandes de liberación
sostenida. Si tal argumento existe, tendría que venir de un proceso aún no
incluido — replicación del fago, degradación programada de la bead, o una
ventana de protección larga con reinfección por *Ralstonia*. **La etapa R
prueba justamente la primera vía.**

### Etapa R (replicación) — reproducir

```bash
mcp_server/venv/bin/python scripts/build_replicacion.py     # modelo 2 especies
mcp_server/venv/bin/python scripts/validate_replicacion.py  # Checks A/B/C
mcp_server/venv/bin/python scripts/sweep_replicacion.py     # barrido
mcp_server/venv/bin/python scripts/plot_replicacion.py      # figura
```

El fago deja de ser pasivo: se **amplifica** al infectar a *Ralstonia*. Modelo
depredador-presa espacial (reacción-difusión de 2 especies, `cP` = fago,
`cH` = *Ralstonia*), cinética Lotka-Volterra en pore volume:

```
R_cP = +b·k_inf·cP·cH − k_inact·cP
R_cH = +r_host·cH·(1 − cH/Kcap) − k_inf·cP·cH
```

*Ralstonia* (sésil) coloniza una banda rizosférica cerca de L en su capacidad
de carga; el fago se libera desde la bead y debe llegar y amplificarse.
Número reproductivo básico R₀ ≈ b·k_inf·H₀/k_inact ≈ 4.3 con los placeholders.

#### Verificación (validate_replicacion.py)

Sistema acoplado no lineal, sin solución cerrada. Tres comprobaciones
independientes:

| Check | Qué compara | Resultado |
|---|---|---|
| A — vs ODE | caso bien mezclado vs ODE Lotka-Volterra (scipy) | error 1e-3 tras apretar `rtol` |
| B — invariante | Mprod = b·Hinf (cada lisis produce b fagos) | 1.5e-15 (exacto) |
| B — balance fago | M(t) = M(0) + Mprod − Minact | 1.3e-7 |
| C — límite H₀→0 | sin hospedador ⇒ M(t) = M(0)·e^(−k·t) | 1.0e-3 |

Detalle numérico revelado por el Check A: el sistema es **stiff y amplifica
~170×**, así que la tolerancia por defecto del solver (~1e-3) se propaga a ~1 %
en el pico. Al apretar `rtol` a 1e-6 el FEM converge a la ODE — confirmando que
la discrepancia era el solver, no el modelo. El build de producción usa
`rtol = 1e-4`.

#### Hallazgo: la métrica importa, y la robusta favorece la sostenibilidad

El barrido reveló que el sistema es un **ciclo depredador-presa con retardo**:
*Ralstonia* crece, el fago la aplasta, el patógeno **rebrota**. Por eso la
supervivencia en un instante fijo es **frágil** (captura una fase del ciclo).
La métrica robusta y biológicamente relevante es la **carga acumulada de
patógeno** ∫H(t)/H₀ dt.

| Métrica | Óptimo | Lectura |
|---|---|---|
| Carga acumulada (robusta) | r_bead = 300 µm, gel lento | **liberación sostenida** |
| Supervivencia final (frágil) | r_bead = 75 µm (óptimo interior) | depende de la fase |
| Mínimo alcanzado | r_bead = 300 µm | liberación sostenida |

Dos de tres métricas —incluida la robusta— favorecen **beads grandes de
liberación lenta**. Esto **invierte** la conclusión de las Etapas 2–3. Nota de
honestidad: la conclusión depende de la métrica temporal elegida, y con estos
placeholders el biocontrol es solo parcial (la carga baja a ~72 %, no se
erradica). Lo robusto es la **dirección**: la replicación da valor a la
sostenibilidad que el transporte pasivo no daba.

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
