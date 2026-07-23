# Research Skills para Claude

## 1. Antes de la investigación (Discovery)

Objetivo: encontrar un problema relevante, demostrar novedad y planificar el estudio.

| Prioridad | Skill | Función |
|-----------|---------|----------|
| ⭐⭐⭐⭐⭐ | Literature Search | Buscar literatura en PubMed, OpenAlex, Semantic Scholar, Crossref, arXiv. |
| ⭐⭐⭐⭐⭐ | Bibliometric Analysis | Co-citation, bibliographic coupling, redes de autores, instituciones, keywords, evolución temática. |
| ⭐⭐⭐⭐⭐ | Research Gap Finder | Detectar vacíos de investigación a partir de cientos de artículos. |
| ⭐⭐⭐⭐⭐ | Novelty Checker | Comparar una idea con la literatura y estimar su novedad. |
| ⭐⭐⭐⭐ | Citation Network Explorer | Explorar redes de citación y artículos fundamentales. |
| ⭐⭐⭐⭐ | Keyword Evolution | Analizar la evolución temporal de palabras clave. |
| ⭐⭐⭐⭐ | Patent Search | Buscar patentes relacionadas (Google Patents, Espacenet, USPTO). |
| ⭐⭐⭐⭐ | Funding Landscape | Identificar agencias y convocatorias que financian el tema. |
| ⭐⭐⭐⭐ | Competitor Lab Mapper | Detectar grupos de investigación líderes. |
| ⭐⭐⭐⭐ | Journal Landscape | Analizar qué revistas publican el tema. |
| ⭐⭐⭐⭐ | Experimental Design | Diseñar experimentos robustos. |
| ⭐⭐⭐⭐ | Sample Size Calculator | Calcular tamaño de muestra. |
| ⭐⭐⭐⭐ | Statistical Test Selector | Seleccionar la prueba estadística adecuada. |
| ⭐⭐⭐ | Variable Checker | Detectar variables confusoras. |
| ⭐⭐⭐ | Protocol Reviewer | Revisar protocolos experimentales. |

---

## 2. Durante la investigación

Objetivo: producir resultados reproducibles y figuras de calidad editorial.

| Prioridad | Skill | Función |
|-----------|---------|----------|
| ⭐⭐⭐⭐⭐ | Figure Reviewer | Revisa figuras con estándares de revistas Q1 (Nature, ACS, Cell, etc.). |
| ⭐⭐⭐⭐⭐ | Figure Generator | Genera figuras multipanel listas para publicación. |
| ⭐⭐⭐⭐⭐ | R ggplot Expert | Convierte gráficos básicos en figuras de calidad editorial usando ggplot2. |
| ⭐⭐⭐⭐ | Statistical Reviewer | Verifica supuestos estadísticos y propone pruebas adecuadas. |
| ⭐⭐⭐⭐ | Data Cleaning | Detecta NA, duplicados, outliers y errores. |
| ⭐⭐⭐⭐ | Code Reviewer | Revisa código R, Python o MATLAB. |
| ⭐⭐⭐⭐ | Computational Reproducibility | Configura renv, Docker, semillas y reproducibilidad. |
| ⭐⭐⭐ | Color Accessibility Checker | Comprueba compatibilidad con daltonismo. |
| ⭐⭐⭐ | Figure Consistency Checker | Homogeneiza el estilo de todas las figuras. |

### Estándares para figuras Q1

- Fondo blanco.
- Sin grid innecesario.
- Tipografía Arial/Helvetica.
- Tamaños de fuente consistentes.
- Paneles A, B, C...
- Paletas aptas para daltónicos.
- Exportación en PDF, SVG y TIFF (600–1200 dpi).
- Compatibilidad con Nature, Science, Cell, ACS, IEEE, Elsevier, Springer y Wiley.

Paquetes recomendados:

- ggplot2
- patchwork
- cowplot
- ggtext
- ggsci
- viridis
- colorspace
- ragg

---

## 3. Después de obtener resultados

Objetivo: validar conclusiones antes de escribir el manuscrito.

| Prioridad | Skill | Función |
|-----------|---------|----------|
| ⭐⭐⭐⭐⭐ | Hypothesis Verifier | Evalúa si los resultados apoyan la hipótesis sin sobreinterpretar los datos. |
| ⭐⭐⭐⭐⭐ | Paper Reviewer | Simula una revisión tipo Nature/Science. |
| ⭐⭐⭐⭐⭐ | Reviewer Simulator | Genera comentarios de Reviewer 1, Reviewer 2 y Editor. |
| ⭐⭐⭐⭐ | Statistical Consistency Checker | Comprueba coherencia entre tablas, figuras y texto. |
| ⭐⭐⭐⭐ | Overclaim Detector | Detecta afirmaciones exageradas ("demuestra", "confirma", etc.). |
| ⭐⭐⭐⭐ | Reproducibility Checker | Evalúa si el estudio puede reproducirse. |
| ⭐⭐⭐⭐ | Journal Matcher | Recomienda revistas adecuadas. |
| ⭐⭐⭐ | Graphical Abstract Designer | Diseña el graphical abstract. |

---

## 4. Publicación

Objetivo: facilitar el envío y responder a revisores.

| Prioridad | Skill | Función |
|-----------|---------|----------|
| ⭐⭐⭐⭐ | Cover Letter Writer | Genera la carta al editor. |
| ⭐⭐⭐⭐ | Reviewer Response Generator | Responde comentarios de revisores. |
| ⭐⭐⭐⭐ | Supplement Formatter | Organiza el material suplementario. |
| ⭐⭐⭐⭐ | Reference Auditor | Verifica referencias y DOI. |
| ⭐⭐⭐⭐ | Journal Formatter | Adapta el manuscrito a la revista objetivo. |
| ⭐⭐⭐⭐ | Ethical Compliance Checker | Revisa PRISMA, CONSORT, STROBE, ARRIVE, etc. |
| ⭐⭐⭐ | AI Disclosure Checker | Comprueba cumplimiento de políticas de uso de IA. |
| ⭐⭐⭐ | Plagiarism Risk Checker | Detecta posibles problemas de similitud. |

---

# Skills transversales

Estos acompañan todo el proyecto.

| Skill | Función |
|--------|----------|
| Research Memory | Mantiene el contexto completo del proyecto. |
| Reproducible Workflow Builder | Genera la estructura reproducible del proyecto (R, Quarto, renv, Docker). |
| Manuscript Consistency Checker | Verifica consistencia entre texto, tablas, figuras y referencias. |
| Research Project Auditor | Auditoría integral antes del envío del artículo. |

---

# Repositorios encontrados

## 1. agent-research-skills ⭐⭐⭐⭐⭐

https://github.com/lingzhi227/agent-research-skills

Incluye más de 30 Skills para:

- Literature Search
- Deep Research
- Literature Review
- Citation Management
- Experiment Design
- Data Analysis
- Paper Assembly
- Slide Generation

---

## 2. medical-research-skills ⭐⭐⭐⭐⭐

https://paper-banana.org/paper-skills/medical-research-skills

Más de 500 Skills orientadas a:

- PubMed
- Revisiones sistemáticas
- Meta-análisis
- Transcriptómica
- RNA-seq
- Single-cell
- Escritura científica

---

## 3. Claude-Code-Skills-for-Academics

https://github.com/aspi6246/Claude-Code-Skills-for-Academics

Enfocado en:

- Investigación académica
- Reproducibilidad
- Beamer
- Auditoría de código

---

## 4. Claude Skills

https://lcrawfurd.github.io/claude-skills/

Incluye herramientas para:

- Paper Review
- Reproducibilidad
- Auditoría metodológica

---

# Skills específicos para figuras

## Nature Figure ⭐⭐⭐⭐⭐

Genera figuras listas para publicación en revistas Q1.

Características:

- SVG
- PDF
- TIFF
- Texto editable
- Multipanel
- Compatible con Nature

---

## Bio Data Visualization ggplot2

Especializado en:

- Heatmaps
- Volcano plots
- Boxplots
- Scatter plots
- Figuras científicas con ggplot2

---

# Top 10 Skills recomendados

1. Literature Search
2. Bibliometric Analysis
3. Research Gap Finder
4. Novelty Checker
5. Experimental Design
6. Statistical Test Selector
7. Figure Reviewer
8. Statistical Consistency Checker
9. Paper Reviewer
10. Reviewer Response Generator