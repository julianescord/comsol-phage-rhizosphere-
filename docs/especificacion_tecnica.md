# Especificación técnica: Modelo FEM de liberación controlada en la rizosfera

Adaptado de la metodología de Dosmar et al. (2021), *"Compartmental and COMSOL Multiphysics 3D Modeling of Drug Diffusion to the Vitreous Following the Administration of a Sustained-Release Drug Delivery System"*, Pharmaceutics 13(11):1862 (`../pharmaceutics-13-01862.pdf`).

Ese paper resuelve un problema estructuralmente idéntico al nuestro: un dispositivo de liberación sostenida (hidrogel) libera un fármaco hacia tejidos en capas, hasta alcanzar un compartimento objetivo (el vítreo). Nosotros reemplazamos "tejido ocular en capas" por "suelo/rizosfera" y "vítreo" por "superficie radicular". El método COMSOL que usan —**Transport of Diluted Species in Porous Media**, estudio *Time-Dependent*, geometría axisimétrica generada por revolución de planos de trabajo 2D— es directamente reutilizable.

## 1. Objetivo del modelo

Predecir la concentración del agente activo (fertilizante, agroquímico o bioestimulante) en función del tiempo y la posición, desde su liberación en una matriz/cápsula embebida en el suelo hasta su llegada a la superficie radicular, incluyendo pérdidas por sorción y degradación en el trayecto.

> **Pendiente de definir con el usuario:** identidad del agente activo, mecanismo de liberación de la matriz (difusión pasiva, hinchamiento, biodegradación), y escala del primer modelo (cápsula única vs. sistema radicular completo). Los parámetros de este documento son placeholders — reemplazar con datos propios o de literatura.

## 2. Dominios geométricos

Igual que el paper construye capas del ojo como planos de trabajo 2D revolucionados, aquí se propone una geometría **axisimétrica** (más barata que 3D completo) con estos dominios concéntricos:

1. **Matriz/cápsula de liberación** — esfera o cilindro con el agente encapsulado.
2. **Zona de suelo cercano (rizosfera)** — anillo alrededor de la cápsula, propiedades modificadas por actividad radicular (pH, exudados, densidad microbiana).
3. **Suelo a granel (bulk soil)** — dominio exterior, propiedades de suelo "normal".
4. **Superficie/volumen radicular** — frontera o dominio delgado que actúa como sumidero.

Si se sigue el atajo metodológico del paper (input function empírico en vez de resolver la difusión interna de la cápsula), el dominio 1 puede colapsarse a una **condición de frontera de flujo entrante** en vez de un dominio resuelto explícitamente — ver sección 5.

## 3. Físicas por dominio

| Dominio | Interfaz COMSOL | Ecuación gobernante |
|---|---|---|
| Matriz de liberación (si se resuelve explícitamente) | Transport of Diluted Species | ∂c/∂t = ∇·(D∇c) |
| Suelo (rizosfera + bulk) | Transport of Diluted Species in Porous Media | ∂(εc)/∂t + ∇·(-Dₑ∇c + **u**c) = R |
| Flujo de agua en suelo (si no saturado) | Richards' Equation | ∂θ(h)/∂t = ∇·[K(h)∇(h+z)] |
| Sorción suelo-soluto | Reacción o "Adsorption" node | c_sorbed = Kf·c^(1/n) (Freundlich) o Kd·c (lineal) |
| Degradación microbiana | Reaction term de primer orden | R_deg = -k_deg·c |
| Captación radicular | Sumidero de frontera/volumen | J_uptake = Vmax·c/(Km+c) (Michaelis-Menten) o k_upt·c |

**Nota de acoplamiento:** el paper resuelve *todas* las capas (córnea, esclera, coroides, retina, vítreo) con la **misma interfaz** (Transport of Diluted Species in Porous Media) simplemente variando las propiedades de transporte por capa, unidas con "Form Union". Se recomienda el mismo enfoque aquí: una sola interfaz de transporte en medios porosos para rizosfera + bulk soil, diferenciando propiedades por dominio, en vez de acoplar múltiples interfaces físicas distintas. Esto reduce enormemente la complejidad de la primera versión del modelo.

## 4. Condiciones iniciales y de frontera

- **Concentración inicial:** c = 0 en todos los dominios de suelo (como en el paper).
- **Frontera de entrada (cápsula → rizosfera):** flujo entrante definido por la función de liberación C_H(t) — ver sección 5.
- **Frontera exterior (borde del dominio de suelo):** salida libre o concentración de fondo, según si se modela una maceta cerrada o un volumen de suelo abierto.
- **Frontera/dominio radicular:** sumidero (uptake), ver tabla de la sección 3.
- **Simetría axial:** eje de revolución con condición de flujo nulo (estándar en geometría axisimétrica de COMSOL).

## 5. Función de entrada: liberación desde la matriz

El paper evita resolver la difusión dentro del hidrogel y en su lugar **ajusta una curva empírica** a datos de liberación in vitro:

```
C_H(t) = -4.709·ln(t) + 34.822      [Ec. 1 del paper, para su sistema]
```

Para nuestro caso, replicar el procedimiento:
1. Obtener (o generar experimentalmente) una curva de liberación acumulada del agente activo desde la matriz elegida.
2. Ajustar una función (logarítmica, exponencial, o modelo de Higuchi/Korsmeyer-Peppas según el mecanismo) a esos datos.
3. Usar esa función como condición de flujo entrante en la interfaz de frontera cápsula→suelo, vía una función interpolada o analítica en COMSOL (`Definitions > Functions`).

Esto es lo que permite saltarse el módulo de difusión interna de la matriz en la primera versión del modelo — **reduce el número de módulos de licencia necesarios** (no hace falta resolver hinchamiento/poroelasticidad de entrada).

## 6. Parámetros a definir (tabla estilo Tabla 1 del paper)

| Parámetro | Símbolo | Valor (placeholder) | Fuente |
|---|---|---|---|
| Coeficiente de difusión efectivo en suelo | Dₑ | — | Literatura / calibración |
| Porosidad del suelo | ε | ~0.4–0.5 (típico) | Caracterización de suelo propio |
| Conductividad hidráulica saturada | Ksat | — | Ensayo de suelo / literatura |
| Parámetros van Genuchten (retención de agua) | α, n, θr, θs | — | Base de datos de suelo (ROSETTA, etc.) |
| Coeficiente de sorción (Kd o Kf, n) | Kd / Kf | — | Ensayo de batch / literatura |
| Constante de degradación | k_deg | — | Literatura o ensayo de incubación |
| Vmax, Km captación radicular | Vmax, Km | — | Literatura de fisiología radicular |
| Función de liberación | C_H(t) | ver sección 5 | Ensayo in vitro propio |

## 7. Estudios y configuración numérica

- **Tipo de estudio:** Time-Dependent (igual que el paper: 100 h con muestreo cada 10 h para su caso; para rizosfera, el horizonte temporal depende de la vida útil del sistema de liberación — puede ser días a semanas).
- **Mallado:** el paper usa tamaño "Normal" por defecto. Recomendado refinar en las interfaces delgadas (cápsula-suelo, superficie radicular) por los gradientes de concentración esperados ahí.
- **Solver:** advertencia de escalas — la difusión dentro de la matriz (si se resuelve) es mucho más rápida que el transporte en suelo; si se combinan, cuidado con problemas *stiff* (usar solver time-dependent con paso adaptativo, BDF).

## 8. Plan de complejidad progresiva

1. **Etapa 1:** liberación pura en suelo homogéneo, sin flujo de agua ni raíz — validar contra solución analítica de difusión esférica/cilíndrica.
2. **Etapa 2:** añadir sorción + degradación (reacciones) en el suelo.
3. **Etapa 3:** acoplar flujo de agua no saturado (Richards) y advección.
4. **Etapa 4:** añadir sumidero radicular (frontera simple, luego geometría de raíz explícita).
5. **Etapa 5 (opcional):** 3D completo, múltiples cápsulas, heterogeneidad de suelo, calibración/optimización de parámetros contra datos experimentales.

## 9. Salidas esperadas / post-procesamiento

- Curvas de concentración vs. tiempo en puntos de interés (superficie radicular, borde de rizosfera).
- Mapas de concentración 2D/3D en instantes clave.
- Tiempo hasta alcanzar concentración umbral (terapéutica/efectiva) en la raíz — análogo directo al análisis de umbral terapéutico del paper (0.007 y 0.024 mg/mL para vancomicina).
- Fracción de agente perdida por degradación vs. la que llega efectivamente a la raíz (balance de masa).
