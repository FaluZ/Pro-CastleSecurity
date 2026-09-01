# Arquitectura de Proyecto-Pegazus

## Objetivo

Herramienta local de análisis de proyectos con cuatro dominios de detección: malware genérico,
EtherHiding, Contagious Interview e inyecciones de código genéricas. Cada dominio se implementa
como un **módulo de análisis independiente** sobre una base común, para poder añadirlos uno por
uno sin reestructurar el sistema.

## Componentes

```
┌─────────────┐      HTTP       ┌──────────────────┐      HTTP       ┌────────────────────┐
│  Frontend   │ ───────────────▶│     Backend       │ ───────────────▶│   analyzer-js       │
│  (React)    │◀─────────────── │    (FastAPI)      │◀─────────────── │  (Node/TS, scaffold) │
└─────────────┘                 └────────┬──────────┘                 └────────────────────┘
                                          │
                                          ▼
                                    ┌───────────┐
                                    │  SQLite   │
                                    │ (scans,   │
                                    │ findings) │
                                    └───────────┘
```

- **Backend (Python/FastAPI)**: expone la API REST, orquesta los escaneos y contiene el motor de
  módulos de análisis. Es la fuente de verdad de los datos (SQLite vía SQLAlchemy).
- **analyzer-js (Node/TypeScript)**: servicio HTTP separado, pensado para el análisis profundo de
  AST de JavaScript/npm que necesitarán los módulos de EtherHiding y Contagious Interview. En el
  MVP es un scaffold sin lógica (`POST /analyze` devuelve `{ findings: [] }`); se elige Node en vez
  de reimplementar un parser de JS en Python porque el ecosistema de AST de JS (acorn/@babel) es
  muchísimo más maduro ahí.
- **Frontend (React/Vite)**: dashboard para lanzar escaneos, ver progreso y explorar hallazgos.

## Motor de módulos (`backend/pegazus/modules/`)

Cada dominio de detección implementa `AnalysisModule` (`modules/base.py`):

```python
class AnalysisModule(ABC):
    name: str
    def scan_project(self, context: ScanContext) -> list[ModuleFinding]: ...  # opcional, una vez por escaneo
    def scan_file(self, file_path: Path, context: ScanContext) -> list[ModuleFinding]: ...  # por archivo
```

El orquestador (`core/orchestrator.py`) no conoce los módulos concretos: los obtiene de
`modules/registry.py` y los invoca sobre cada archivo enumerado por `core/walker.py`. Añadir un
módulo nuevo (inyecciones, EtherHiding, Contagious Interview) es:

1. Crear `modules/<nombre>/` con una clase que implemente `AnalysisModule`.
2. Registrarla en `modules/registry.py`.

No requiere tocar el orquestador, la API ni el frontend (la tabla `Finding` ya es genérica:
`module`, `severity`, `title`, `description`, `file_path`, `evidence`, `rule_id`).

## Módulo MVP: malware genérico (`modules/malware/`)

Tres técnicas combinadas por archivo:

1. **YARA** (`yara_scanner.py`): reglas propias en `rules/*.yar` (PowerShell ofuscado, indicadores
   de webshell, patrones base64+ejecución, string de prueba EICAR). Se pueden añadir más `.yar`
   (p. ej. rulesets de YARA-Forge) sin tocar código.
2. **Hash lookup** (`hash_lookup.py`): tabla local de hashes SHA256 conocidos. Sin llamadas de red
   por defecto — la herramienta es local/offline-first.
3. **Heurísticas** (`heuristics.py`): entropía de Shannon (empaquetado/cifrado), discrepancia entre
   cabecera del archivo y extensión, patrones de descarga+ejecución encadenada.

## Módulo: EtherHiding (`modules/etherhiding/`)

Cubre la inyección de código en archivos de configuración de build (o en el shim de entrada de
apps Electron instaladas por usuario) y la resolución de C2 vía transacciones de Ethereum. La
premisa de diseño: **los strings literales dejan de servir en cuanto el atacante cambia de
ofuscador; las señales estructurales no**, así que el módulo prioriza esas.

1. **Estructurales** (`structural.py`, `baselines.py`) — sobreviven al cambio de ofuscador:
   - Línea anormalmente larga (>400 bytes) en `vite.config.js`, `webpack.config.js`,
     `webpack.mix.js`, `next.config.js`, o en el `index.js`/`main.js` de una app Electron cuando
     está en su ubicación típica empaquetada (`resources/app...`, `app.asar.unpacked`).
   - Cierre de bloque legítimo (`});`, `],`) seguido de un salto grande de espacios/tabs y más
     código en la misma línea — patrón de código añadido al final de una línea existente.
   - Tamaño de archivo muy distinto a una línea base conocida, para shims pequeños y estables de
     apps Electron (`baselines.py`; lista deliberadamente pequeña y ampliable).
2. **Marcadores literales conocidos** (`rules/etherhiding.yar`, vía el mismo motor YARA
   compartido en `modules/yara_utils.py` que usa el módulo de malware) — útiles hoy, van a
   caducar: `global.i="A8-...`, `global['!']='...`, `global['e']='app-*-eval'`, el patrón
   `windowsHide` + `detached` + `spawn(...'node'...'-e'...)`, y referencias a proveedores públicos
   de RPC de Ethereum (`1rpc.io`, `drpc.org`, `publicnode.com`, `blockscout.com`, `blastapi.io`).
   `createRequire(import.meta.url)` se marca solo como `info`: no es malicioso por sí solo, es
   scaffolding legítimo de ESM.
3. **Nombres de archivo sospechosos** (`filenames.py`): artefactos conocidos de esta campaña
   (`SvcHostUpdate.py`, `97icr5.py`, `*.inz.*`, `*.QUARANTINED`).
4. **Historial completo de git, no solo HEAD** (`git_history.py`, `scan_project`): busca los
   mismos marcadores literales con `git log --all -G<patrón>` sobre todos los commits — detecta
   código que se añadió y luego se "limpió" pero sigue enterrado en un commit viejo. Una sola
   llamada de pickaxe combinada encuentra los commits candidatos; solo esos se inspeccionan en
   detalle, para no pagar el costo de una llamada a git por patrón en repos grandes.

**Deliberadamente fuera del ruleset**: la IP del C2 (`23.27.13.135`). El mecanismo la resuelve
dinámicamente desde una transacción de Ethereum, así que puede cambiar en cualquier momento — un
IOC de IP fija caducaría de inmediato y daría falsa confianza.

## Módulo: Contagious Interview (`modules/contagious_interview/`)

Cubre la persistencia vía auto-ejecución de tareas de VS Code — un patrón característico de esta
campaña para lograr ejecución con solo abrir la carpeta del proyecto en el editor, sin build ni
confirmación del usuario. Es un chequeo de **proyecto**, no de archivo: solo mira dos rutas fijas
(`vscode_tasks.py`):

- `.vscode/tasks.json` con `"runOn": "folderOpen"` **y** `.vscode/settings.json` con
  `"task.allowAutomaticTasks"` habilitado (`true` o `"on"`) → severidad **alta**.
- Si además la tarea usa `"reveal": "never"` + `"hide": true` (oculta la ejecución en la terminal
  integrada) → severidad **crítica**.

## Detección en el flujo de trabajo (git hooks, CI y `safe-install`)

Más allá del escaneo bajo demanda, el CLI expone comandos pensados para engancharse en el ciclo de
vida de git, GitHub Actions y pnpm (ver `pegazus install-hooks` y el README para la instalación):

### Distribución de los hooks: `.githooks/`, no `.git/hooks/`

`.git/hooks/` es local a cada máquina y nunca se puede comitear: un hook copiado ahí solo protege a
quien lo copió. `pegazus install-hooks <repo>` en cambio escribe los scripts en `<repo>/.githooks/`
(un directorio normal, versionable) y corre `git config core.hooksPath .githooks` en ese repo —
así `.githooks/` viaja con el commit y protege a cualquiera que clone el repo, aunque cada quien
todavía tenga que activarlo localmente una vez (`core.hooksPath` es config de git, no un archivo
versionado). Por defecto también escribe dos workflows de GitHub Actions en `.github/workflows/`
como respaldo server-side, que no dependen de que nadie active nada localmente:

- `pegazus-scan.yml`: corre `scan-diff` en cada push/PR — mismo chequeo rápido que los hooks
  locales, pero server-side; cubre a quien comitea sin el hook instalado o lo salta con
  `--no-verify`.
- `pegazus-full-scan.yml`: corre `pegazus scan` completo en cron semanal — cubre el historial de
  git y las reglas de proyecto que los hooks/workflow de arriba se saltan a propósito por
  velocidad.

Los scripts de hooks viven como datos empaquetados en `pegazus/hook_templates/` y los workflows en
`pegazus/ci_templates/` (declarados en `[tool.setuptools.package-data]` de `pyproject.toml`) —
`install-hooks` los copia desde ahí, no desde el repo de Pegazus en disco, así que funciona igual
con un `pip install -e .` en desarrollo que con el paquete ya instalado en otra máquina/runner.
Ambos workflows traen un `TODO` explícito para el paso "Instalar Pegazus": no hay forma de
adivinar dónde va a estar publicado el paquete para una organización dada.

- `pegazus scan-staged` (hook `pre-commit`): analiza solo los archivos en stage. Bloquea el commit
  (exit 1) si hay hallazgos alta/crítica — es la única capa que puede prevenir, no solo alertar,
  porque corre antes de que el commit exista.
- `pegazus scan-diff` (hooks `post-merge` / `post-checkout`): analiza los archivos que cambiaron
  en un `git pull`/`git clone`/`git checkout`. Git no tiene forma de bloquear un fast-forward antes
  de que los archivos toquen disco, así que esto es alerta inmediata, no prevención.
- `pegazus safe-install`: corre `pnpm install` (pnpm deja los scripts de lifecycle de las
  dependencias pendientes de aprobación por defecto desde la v10 — no hace falta pasarle ninguna
  flag, se verificó empíricamente antes de construir esto), analiza `node_modules`, y solo corre
  `pnpm approve-builds --all` (que ejecuta los scripts pendientes) si el análisis sale limpio. Esta
  sí es prevención real para un payload que vive en un script de instalación (p.ej. el gusano
  Shai-Hulud en npm): simplemente nunca llega a ejecutarse si se detecta algo. **No** protege
  contra un payload que se ejecuta al importar el paquete en vez de en un script de instalación
  (así operó parte del compromiso de chalk/debug en npm de 2025) — para eso, lo único que hay es
  que el análisis de `node_modules` corre de todas formas y reporta lo que encuentre, aunque no
  pueda "prevenirlo" sin más. Ver también la sección "Por qué pnpm y no npm" del README.

`scan-staged`, `scan-diff` y `safe-install` reutilizan el mismo registro de módulos
(`modules/registry.py`) que el escaneo completo, pero solo corren los chequeos por archivo
(`scan_file`) — no el barrido de historial de git ni las reglas de proyecto (`scan_project`), que
son más costosas y están pensadas para un barrido periódico completo, no para cada commit/pull.
Esto también significa que ni los hooks ni los workflows de CI necesitan cambios cuando se agrega
un módulo de detección nuevo: solo llaman a estos comandos, que ya recorren el registro completo.

**Fuera de alcance, deliberadamente**: un "listener" que intercepte la ejecución de *cualquier*
proceso en el sistema antes de que corra (más allá del caso concreto de scripts de instalación que
sí cubre `safe-install`) requeriría un servicio en background con privilegios elevados y hooks a
nivel de sistema operativo (p. ej. eventos de creación de proceso vía WMI en Windows) — una
categoría de capacidad distinta a un escáner de archivos, con mayor riesgo de interferir con
procesos legítimos. No se implementó sin una decisión explícita al respecto.

## Modelo de datos

- `Scan`: una ejecución de análisis sobre una ruta (`target_path`), con estado y contadores.
- `Finding`: un hallazgo de un módulo, ligado a un `Scan`, con severidad, evidencia y archivo.

## Por qué estas decisiones

- **Escaneo por ruta local, no subida de archivos**: es una herramienta local; el backend accede
  directamente al sistema de archivos donde corre.
- **SQLite**: cero configuración, adecuado para una herramienta de un solo usuario/máquina.
- **Sin llamadas de red por defecto**: los módulos de detección funcionan offline; integración con
  servicios externos (VirusTotal, MalwareBazaar) queda como opción explícita, no obligatoria.
