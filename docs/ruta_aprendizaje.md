# Ruta de aprendizaje: habilidades para el modelo de liberación controlada en rizosfera

Organizado por competencia. Cada bloque indica qué necesitas saber hacer (no solo saber), y por qué importa para este modelo específico.

## 1. Transporte de masa y medios porosos (base física)

**Qué debes poder hacer:** derivar/entender la ecuación de advección-dispersión-reacción, distinguir difusión molecular de dispersión hidrodinámica, entender por qué la porosidad y tortuosidad reducen el coeficiente de difusión efectivo respecto al de agua libre.

- Libro de referencia clásico: Jacob Bear, *Dynamics of Fluids in Porous Media* — el estándar del campo, aunque denso; útil como referencia más que lectura lineal.
- Ecuación de van Genuchten (1980) para la curva de retención de agua no saturada — necesaria si usas Richards' Equation. Búscala como "van Genuchten 1980 closed-form equation unsaturated hydraulic conductivity".
- Documentación de COMSOL sobre "Transport of Diluted Species in Porous Media" (en el Application Library y el manual del Subsurface Flow Module) — explica exactamente los términos que necesitas parametrizar.

**Por qué importa aquí:** todo el modelo depende de esta ecuación; es el 80% del entendimiento conceptual necesario antes de tocar el software.

## 2. Cinética de sorción y degradación

**Qué debes poder hacer:** elegir entre isoterma lineal (Kd), Freundlich o Langmuir según el comportamiento de tu agente activo en el suelo; plantear un término de reacción de primer orden para degradación.

- Si tu agente ya tiene estudios de sorción en suelo publicados (frecuente para agroquímicos/fertilizantes registrados), busca directamente el Kd o Kf reportado — evita tener que derivarlo tú mismo.
- Módulo de COMSOL: Chemical Reaction Engineering Module — su documentación tiene ejemplos de cómo implementar isotermas como nodos de reacción.

**Por qué importa aquí:** sin esto, el modelo sobreestima drásticamente cuánto agente llega a la raíz — es habitual que la sorción retenga la mayor parte del compuesto en el suelo.

## 3. Fisiología de captación radicular

**Qué debes poder hacer:** justificar si la captación en tu sistema es mejor descrita por cinética de Michaelis-Menten (saturable, típica de captación activa de nutrientes) o de primer orden (pasiva).

- Línea de investigación de referencia: los trabajos de Tiina Roose y colaboradores sobre modelado matemático de captación de agua y nutrientes por sistemas radiculares — buscar "Roose Fowler mathematical model root nutrient uptake" para encontrar la literatura relevante y los valores típicos de Vmax/Km usados en modelos similares.
- Si tu compuesto no es un nutriente sino un agroquímico/bioestimulante, revisa si existe literatura de captación específica para esa clase de compuesto; si no, el paper de referencia local (Dosmar et al.) te muestra cómo justificar el uso de constantes de permeación de un compuesto químicamente similar cuando no hay datos directos (lo hacen con dexametasona para vancomicina, sección 2.6 del PDF).

**Por qué importa aquí:** es el término menos estandarizado del modelo — probablemente el que requiera más criterio propio o calibración experimental.

## 4. Manejo operativo de COMSOL

**Qué debes poder hacer:** construir geometría multi-dominio, aplicar "Form Union", definir funciones interpoladas/analíticas para condiciones de frontera dependientes del tiempo, mallar con refinamiento localizado, configurar un estudio Time-Dependent con solver adaptativo.

- COMSOL Learning Center (sección de soporte en comsol.com) — tutoriales oficiales gratuitos, incluye casos de "Transport of Diluted Species in Porous Media".
- Application Gallery de COMSOL (comsol.com/models) — busca modelos de ejemplo en las categorías "Subsurface Flow" y "Chemical Species Transport"; son el punto de partida más rápido porque puedes abrir el archivo `.mph` y ver exactamente cómo está configurado cada nodo.
- El paper de referencia local (`../pharmaceutics-13-01862.pdf`, sección 2.6) es en sí mismo un tutorial condensado del flujo de trabajo que necesitas replicar.

**Por qué importa aquí:** es la habilidad "instrumental" — sin ella no puedes traducir la especificación técnica (`especificacion_tecnica.md`) en un modelo real, sin importar cuánto domines la física.

## 5. (Opcional) Scripting con LiveLink

**Qué debes poder hacer:** automatizar la construcción del modelo o barridos paramétricos vía LiveLink for MATLAB.

- Manual "LiveLink for MATLAB User's Guide" (incluido en la documentación de COMSOL una vez instalado).
- Ya te dejé un esqueleto de script en `../scripts/build_rhizosphere_model.m` como punto de partida.

**Por qué importa aquí:** no es imprescindible para un primer modelo, pero se vuelve valioso en la Etapa 5 (calibración/optimización, barridos de parámetros de suelo o de mecanismo de liberación).

## Orden sugerido

1. Bloques 1 y 2 (física + reacciones) — puedes estudiarlos sin tener COMSOL instalado todavía.
2. Bloque 4 en paralelo, empezando con los tutoriales oficiales, apenas tengas acceso a una licencia.
3. Bloque 3 cuando definas con más precisión tu agente activo y sistema radicular objetivo.
4. Bloque 5 solo si el proyecto crece hacia calibración/optimización sistemática.
