# Forja de Skills SOP

[中文](README.md) · [日本語](README_JA.md) · [한국어](README_KO.md) · [English](README_EN.md)

> Convierte documentos de negocio dispersos en un Skill de Claude Code reutilizable.

![Cómo funciona](sop-skill-factory.png)

**Forja de Skills SOP** es un meta-skill de [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Invócalo en cualquier carpeta que contenga materiales de negocio, y la capa programática de Python trabajará junto con la capa semántica del LLM para destilar tus documentos en un `SKILL.md` estructurado y listo para usar.

## Qué problema resuelve

Tienes montones de documentos SOP, manuales de operación y hojas de procesos de aprobación, pero no pueden ser utilizados directamente por Claude Code. La Forja lee estos materiales, identifica automáticamente el tipo de negocio, extrae los elementos clave, valida la integridad y produce un archivo Skill estándar.

## Cómo funciona

![Cómo funciona](Working-principle.png)

**División de responsabilidades**: Python maneja operaciones deterministas (análisis de archivos, renderizado de formatos, validación estructural), mientras que el LLM maneja operaciones semánticas (comprensión de contenido, extracción de información, clasificación de tipos). Cualquier fallo en un módulo de Python activa automáticamente el modo LLM puro como respaldo.

## 9 tipos de Skill compatibles

| Tipo        | Descripción              | Escenarios típicos                                                           |
| ----------- | ------------------------ | ---------------------------------------------------------------------------- |
| sequential  | Flujo lineal             | Onboarding, reembolso de gastos, adquisiciones                               |
| conditional | Ramificación             | Configuración IT, gestión por niveles de cliente                             |
| checklist   | Lista de verificación    | Revisión de código, verificación pre-lanzamiento, auditorías de seguridad    |
| template    | Generación de plantillas | Correos, generación de documentos, informes                                  |
| knowledge   | Conocimiento/Q&A         | FAQ, manuales de producto, interpretación de políticas                       |
| decision    | Apoyo a decisiones       | Selección tecnológica, revisión de propuestas, evaluación de riesgos         |
| monitoring  | Operaciones y monitoreo  | Inspección de sistemas, resolución de problemas, optimización de rendimiento |
| approval    | Flujo de aprobación      | Solicitudes de permiso, aprobaciones de compra, firma de contratos           |
| hybrid      | Mixto/compuesto          | SOPs complejos con múltiples subprocesos                                     |

## Inicio rápido

### Requisitos previos

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) instalado y con sesión iniciada
- Python 3.9+ (para la capa programática; se degrada automáticamente si no está disponible)

### Instalación

```bash
git clone https://github.com/suzibinjelly/sop-skill-factory.git
cd sop-skill-factory
```

Copia o enlaza el directorio `sop-skill/` a `.claude/skills/`:

```bash
# Opción 1: Copia directa
cp -r sop-skill ~/.claude/skills/sop-skill

# Opción 2: Enlace simbólico (más fácil de actualizar)
ln -s "$(pwd)/sop-skill" ~/.claude/skills/sop-skill
```

### Uso

Abre Claude Code en un directorio que contenga tus materiales de negocio y escribe:

```
/sop-skill
```

O en lenguaje natural:

```
Convierte el contenido de esta carpeta en un Skill
```

La Forja te guiará a través de todo el proceso de destilación.

## Estructura del proyecto

```
sop-skill/
├── SKILL.md                   # Archivo de instrucciones del meta-skill
├── python/
│   ├── scanner.py             # Escaneo de archivos + análisis multiformato
│   ├── classifier.py          # Señales de palabras clave + preclasificación de tipos
│   ├── schema.py              # Registro de elementos + modelos de datos Pydantic
│   ├── validator.py           # Validación estructural JSON + detección de conflictos
│   ├── renderer.py            # Renderizado de plantillas Jinja2
│   ├── quality.py             # Verificaciones de puerta de calidad
│   └── requirements.txt       # Dependencias de Python
└── templates/                 # Plantillas de salida Jinja2 para 9 tipos
    ├── sequential.md.j2
    ├── conditional.md.j2
    ├── checklist.md.j2
    ├── template.md.j2
    ├── knowledge.md.j2
    ├── decision.md.j2
    ├── monitoring.md.j2
    ├── approval.md.j2
    └── hybrid.md.j2
```

## Formatos de archivo compatibles

`.md` `.txt` `.yaml` `.yml` `.json` `.csv` `.docx` `.pdf` `.xlsx` `.pptx` `.html` `.htm`

## Contacto

<img src="contact.jpg" width="20%" alt="Contacto" />

## Licencia

[MIT](LICENSE)
