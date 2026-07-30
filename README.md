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
docs/             Especificación técnica (histórica), plan de etapas, datos de fagos
docs/summary/     Informe final consolidado (resumen.html) — metodología + hallazgos
scripts/          Construcción y validación de modelos (fuente de verdad)
models/           Artefactos .mph y salidas — NO versionados, se regeneran
mcp_server/       Servidor MCP que expone COMSOL como herramientas
Markdown/         Paper de referencia convertido a texto
```

Los archivos `.mph` **no se versionan**: son reproducibles ejecutando los
scripts. El código es la fuente de verdad, no el binario.

Dentro de `scripts/` hay dos categorías, reconocibles por el nombre:

- **Pipeline de simulación** (`build_*`, `validate_*`, `sweep_*`, `plot_*`,
  y el módulo compartido `analytic.py`) — construyen, verifican y barren los
  modelos COMSOL. Requieren `mcp_server/venv` (con `mph`).
- **Herramientas de reporte vía IA externa** (`analisis_datos_deepseek.py`,
  `analisis_nano.py`) — no simulan nada; leen resultados ya generados y le
  piden a un modelo de lenguaje (Llama 3.1 70B vía API de NVIDIA) que
  redacte texto/HTML a partir de ellos. Ver detalle abajo.

Algunos documentos de `docs/` (`especificacion_tecnica.md`,
`ruta_aprendizaje.md`, `conexion.md`) son **material histórico**: reflejan el
plan o las opciones consideradas *antes* de construir el modelo, no lo que
efectivamente se hizo. Cada uno tiene una nota al inicio señalando esto y
apuntando a la fuente vigente.

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
| 4 | Flujo de agua y advección (campo uniforme impuesto) | ✅ verificada (con salvedad geométrica) |
| F+R | **Combinado: flujo + replicación (2 interfaces acopladas)** | ✅ verificada |
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

### Etapa 4 (flujo de agua) — reproducir

```bash
mcp_server/venv/bin/python scripts/build_flujo.py       # modelo con advección
mcp_server/venv/bin/python scripts/validate_flujo.py    # Checks A/B/C
mcp_server/venv/bin/python scripts/sweep_flujo.py        # barrido de Péclet
mcp_server/venv/bin/python scripts/plot_flujo.py         # figura
```

Añade **advección**: el agua del suelo arrastra el fago. La pregunta es si el
flujo ayuda al fago a alcanzar la raíz antes de inactivarse (la longitud de
penetración difusiva es solo ~0.36 mm, Etapa 3).

#### Salvedad geométrica importante (por qué el flujo es *uniforme*)

El plan original era resolver Darcy/Richards con **transpiración convergente**
hacia la raíz. No fue posible de forma limpia, por una razón geométrica real —
no un fallo de implementación:

- Resolver Darcy con **recarga distribuida** rompía el balance de masa: la
  fuente de fluido introduce un término espurio `c·∇·u` en la forma
  conservativa del transporte.
- Darcy por **gradiente de presión** daba Péclet ~10⁴ (geometría fina + suelo
  permeable) con oscilaciones numéricas severas.
- Un campo **convergente** hacia la raíz esférica envolvente es incompresible
  *solo con una fuente en el centro* (el agua que converge debe originarse en
  algún sitio); cualquier regularización de esa singularidad reintroduce
  `∇·u ≠ 0` y vuelve a romper el balance.

La "raíz esférica envolvente" heredada de las Etapas 2–3 —perfecta para
difusión + reacción— es **incompatible con un flujo advectivo convergente
limpio**. Se verificó numéricamente: el campo convergente regularizado explota
el balance (Mout/M₀ ≈ 1000), mientras un flujo **uniforme** (∇·u = 0 exacto)
lo cierra a &lt; 1 %.

Por eso la Etapa 4 modela un **flujo de fondo uniforme** (riego/percolación que
atraviesa la rizosfera), no transpiración convergente. Es un escenario distinto
pero verificable. La transpiración convergente exigiría rediseñar la geometría
con entrada y salida de agua en fronteras opuestas — trabajo futuro.

#### Verificación y resultado

Los tres checks (balance de masa, límite Pe→0, monotonía) pasan; el balance
cierra a ~1 % (offset de CI). El resultado físico es contundente:

| Pe | fago entregado vivo | inactivado |
|---|---|---|
| 0 (difusión pura) | 1 % | 100 % |
| 5 | 80 % | 21 % |
| 20 | 96 % | 5 % |
| 80 | 99.5 % | 1.3 % |

**El flujo de agua rescata al fago de la inactivación en tránsito.** Sin flujo
casi todo muere antes de llegar; con flujo modesto (Pe ≳ 5) la mayoría llega
viva. Esto relaja la restricción de la Etapa 3 (la bead ya no tiene que estar
sub-milimétricamente pegada a la raíz si hay flujo que transporte el fago).

### Modelo combinado (flujo + replicación) — reproducir

```bash
mcp_server/venv/bin/python scripts/build_flujo_replicacion.py
mcp_server/venv/bin/python scripts/validate_flujo_replicacion.py
mcp_server/venv/bin/python scripts/sweep_flujo_replicacion.py
mcp_server/venv/bin/python scripts/plot_flujo_replicacion.py
```

Cruza los dos hallazgos principales: la **replicación** (que favorece la
liberación sostenida) y el **flujo de agua** (que rescata al fago del tránsito).
Pregunta: ¿el flujo cambia la conclusión sobre la liberación sostenida?

**Detalle técnico — dos interfaces TDS.** El fago (cP) es móvil y se advecta;
*Ralstonia* (cH) es sésil y **no** debe advectarse (con Pe~20 el flujo la
barrería decenas de mm en 21 d). Como en TDS la velocidad es por interfaz, se
usan dos interfaces acopladas por las reacciones cruzadas Lotka-Volterra: `tds`
(fago, con advección) y `tds2` (*Ralstonia*, sésil). Verificado: el invariante
Mprod = b·Hinf cierra a 1.5e-15 y el límite Pe→0 reproduce la etapa de
replicación (dif 1.3 %).

#### Resultado: el flujo refuerza —no invierte— la liberación sostenida

Barrido Pe × r_bead, carga acumulada de *Ralstonia* (menos = mejor):

| Pe \\ r_bead | 25 µm | 75 µm | 150 µm | 300 µm |
|---|---|---|---|---|
| 0 (sin flujo) | 115 % | 96 % | 86 % | **75 %** |
| 5 | 85 % | 74 % | 68 % | **61 %** |
| 20 | 101 % | 90 % | 77 % | **57 %** |

Tres lecturas:

1. **La bead grande (300 µm, liberación sostenida) gana con cualquier flujo** —
   la conclusión de la etapa de replicación no se invierte, se refuerza.
2. **El flujo mejora el biocontrol**, pero con matiz: para la bead grande es
   monótono (75→61→57 %); para beads pequeñas hay un óptimo — Pe = 5 es mejor
   que Pe = 20.
3. **Flujo excesivo puede ser contraproducente** para liberación rápida: con
   bead pequeña + Pe alto, el flujo barre el fago fuera del dominio antes de que
   amplifique. La liberación sostenida es más robusta al flujo porque repone el
   fago barrido. Hay **sinergia bead-grande + flujo**.

### Nota sobre la escala del vehículo

`r_bead` es un parámetro global. Ojo: en la Etapa 1, con D uniforme y medio
infinito, el problema es **auto-similar** (todo escala con a²/D), así que
barrer `r_bead` solo reescala el eje temporal y no discrimina nada. El barrido
solo aporta información cuando se rompe la auto-similitud — es decir, en la
Etapa 2 en adelante: D_bead ≠ D_suelo, una distancia fija a la raíz, o una
constante de inactivación fija.
