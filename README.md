# Proyecto-Pegazus

Sistema local para analizar proyectos de software y detectar:

- **Malware genérico** (YARA + hashes conocidos + heurísticas)
- **EtherHiding** (inyección de código en configs de build + C2 resuelto vía blockchain)
- **Contagious Interview** (persistencia vía auto-ejecución de tareas de VS Code)
- Inyecciones de código genéricas (SAST) — próxima fase

Arquitectura y decisiones de diseño: [docs/architecture.md](docs/architecture.md).

## Componentes

| Componente     | Stack                  | Rol                                                    |
|----------------|-------------------------|---------------------------------------------------------|
| `backend/`     | Python (FastAPI)        | API, orquestador de escaneos, motor de módulos de análisis |
| `analyzer-js/` | Node.js (TypeScript), pnpm | Servicio de análisis de JS/npm (scaffold para fases futuras) |
| `frontend/`    | React + TypeScript + Vite | Dashboard web                                          |

## Por qué pnpm y no npm

Los dos proyectos Node de este repo (`analyzer-js/`, `frontend/`) usan **pnpm**, no npm. No es
preferencia de estilo: npm ejecuta los scripts de instalación (`postinstall`, etc.) de *todas* las
dependencias automáticamente, que es exactamente el vector que se usó en el compromiso de
chalk/debug/etc. en npm (2025, cuenta de un maintainer comprometida por phishing) y en el gusano
Shai-Hulud. pnpm, desde la v10, **bloquea esos scripts por defecto** y exige aprobación explícita
(`pnpm approve-builds`) — lo verificamos en este repo antes de migrar (`esbuild` quedó bloqueado
hasta aprobarlo a mano).

Esto no es una solución completa: no protege contra un payload que corre al *importar* el paquete
en vez de en un script de instalación (así operó parte del compromiso de chalk/debug). Por eso
`pegazus safe-install` (ver más abajo) sigue analizando el contenido de `node_modules` con los
mismos módulos de detección, independientemente de si pnpm bloqueó algo o no.

Instalar pnpm si no está disponible: `corepack enable` (viene con Node ≥16.9) o
`npm install -g pnpm` / `winget install pnpm.pnpm` / `scoop install pnpm`.

## Puesta en marcha (desarrollo)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
uvicorn pegazus.api.main:app --reload
```

API disponible en `http://localhost:8000`. Documentación interactiva en `http://localhost:8000/docs`.

Ejecutar pruebas:

```bash
cd backend
pytest
```

Escanear desde la línea de comandos, sin necesidad del dashboard:

```bash
pegazus scan "C:\ruta\al\proyecto\a\analizar"
```

### analyzer-js

```bash
cd analyzer-js
pnpm install
pnpm run dev
```

Servicio disponible en `http://localhost:4100`. Es un scaffold: `POST /analyze` responde
`{ "findings": [] }` hasta que se implementen los módulos de EtherHiding / Contagious Interview.

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

Dashboard disponible en `http://localhost:5173`. Requiere que el backend esté corriendo en
`http://localhost:8000` (proxy configurado en `vite.config.ts`).

## Uso

1. Levantar el backend (y opcionalmente analyzer-js).
2. Levantar el frontend y abrir el dashboard.
3. En "Nuevo escaneo", indicar la ruta local de un proyecto a analizar.
4. Revisar los hallazgos por severidad y módulo en el detalle del escaneo.

También se puede analizar sin el dashboard: `pegazus scan "<ruta>"` (ver arriba). Esto incluye
carpetas de instalación por usuario de apps Electron (p. ej. `%LOCALAPPDATA%\Discord`,
`%LOCALAPPDATA%\Programs\...`): son una ruta como cualquier otra para el escáner, y los chequeos
estructurales/de línea base del módulo EtherHiding están pensados justamente para ese tipo de
carpeta.

**No incluido todavía** (categorías distintas a un escáner de archivos, pendientes de una decisión
explícita antes de construirlas): una auditoría de persistencia de Windows (tareas programadas,
claves `Run`/`RunOnce`, suscripciones WMI, exclusiones de Defender) y un "listener" que bloquee la
ejecución de *cualquier* proceso del sistema antes de que corra — este último requeriría un
servicio en background con privilegios elevados, a diferencia de todo lo demás en este proyecto.

## Hooks de git y bloqueo de scripts de instalación

Además del escaneo completo bajo demanda, Pegazus se puede enganchar en el flujo de trabajo con
git y pnpm para detectar (y en un caso, bloquear) problemas automáticamente:

| Comando / hook | Cuándo corre | ¿Bloquea? |
|---|---|---|
| `pegazus scan-staged <repo>` + hook `pre-commit` | Antes de cada commit | Sí — aborta el commit si hay hallazgos alta/crítica |
| `pegazus scan-diff <repo> <from> <to>` + hook `post-merge` | Después de `git pull` | No — git no permite bloquear un fast-forward antes de que los archivos toquen disco; es alerta inmediata |
| `pegazus scan-diff <repo> <from> <to>` + hook `post-checkout` | Después de `git clone` / `git checkout` | No, mismo motivo que arriba |
| `pegazus safe-install <repo>` | En vez de `pnpm install` | Sí — pnpm ya deja los scripts de instalación pendientes de aprobación por defecto; solo corre `pnpm approve-builds` (que los ejecuta) si el análisis de `node_modules` sale limpio |
| Workflow `pegazus-scan.yml` (GitHub Actions) | En cada push/PR | Sí, como *required status check* — respaldo server-side: cubre a quien comitea sin el hook local instalado, o lo salta con `--no-verify` |
| Workflow `pegazus-full-scan.yml` (GitHub Actions) | Cron semanal | No bloquea un commit puntual, pero el job falla y avisa — cubre el historial de git y las reglas de proyecto, que los hooks de arriba se saltan a propósito por velocidad |

`scan-staged` y `scan-diff` solo corren los chequeos por archivo (no el barrido de historial de
git completo ni las reglas de proyecto): están pensados para ser rápidos en cada commit/pull. El
barrido completo (`pegazus scan`, o el workflow `pegazus-full-scan.yml`) sigue siendo necesario
para el historial de git y las reglas a nivel de proyecto.

### Instalación: `pegazus install-hooks`

```bash
pegazus install-hooks <ruta-al-repo>
```

Esto NO copia nada a `.git/hooks/` (esa carpeta es local a cada máquina y nunca protege a nadie
más). En cambio escribe los scripts en `<repo>/.githooks/` — un directorio normal, versionable — y
corre `git config core.hooksPath .githooks` en ese repo. Falta un solo paso manual, porque
`core.hooksPath` es config local de git (no viaja en el commit):

```bash
git add .githooks .github/workflows
git commit -m "Instalar hooks y CI de Proyecto-Pegazus"
git push
```

A partir de ahí, cualquiera que clone el repo (Frank, un servidor de build, etc.) recibe
`.githooks/` versionado, pero **todavía tiene que activar el hook localmente una vez**:

```bash
pegazus install-hooks .        # o: git config core.hooksPath .githooks
```

El workflow de GitHub Actions (`pegazus-scan.yml`, escrito junto con los hooks salvo que se use
`--no-workflow`) no depende de este paso — corre server-side sin importar si alguien activó el
hook local o no. **Antes de usarlo**, hay que editar el paso "Instalar Pegazus" dentro de
`.github/workflows/pegazus-scan.yml` y `pegazus-full-scan.yml`: no hay forma de adivinar dónde va a
estar publicado el paquete `pegazus` para tu organización (índice privado, `pip install
git+ssh://...`, submódulo, etc.) — queda marcado con un `TODO` explícito en ambos archivos.

**Repos nuevos que todavía no existen**: para que `git init`/`git clone` copien los hooks
automáticamente sin correr `install-hooks` a mano cada vez, configurar una plantilla global de git
una sola vez (complementario a lo de arriba, no lo reemplaza — sigue haciendo falta comitear
`.githooks/` para que viaje con el repo cuando otra persona lo clona):

```bash
git config --global init.templateDir ~/.git-templates
mkdir -p ~/.git-templates/hooks
```

**Generalización automática**: ni los hooks ni los workflows conocen los módulos de detección de
Pegazus — solo llaman a `pegazus scan-*`, que recorre el registro completo
(`modules/registry.py`). Cuando se agregue un módulo nuevo (inyecciones de código, o lo que sea),
no hay que volver a correr `install-hooks` ni tocar `.github/workflows/`: alcanza con actualizar el
paquete `pegazus` instalado en cada máquina/runner.

## Estado

Base del sistema (arquitectura de módulos, orquestador, API, dashboard) + tres módulos de
detección: **malware genérico** (YARA + hashes + heurísticas), **EtherHiding** (señales
estructurales + marcadores literales + historial de git) y **Contagious Interview** (persistencia
vía tareas de VS Code). Más los hooks de git, `safe-install` y `install-hooks` descritos arriba.
Las inyecciones de código genéricas quedan como próximo módulo, sobre esta misma base.

El ruleset de EtherHiding se validó y se amplió (marcadores literales adicionales, más nombres de
config de build) usando indicadores de una campaña real contra desarrolladores — no son firmas
teóricas. También se corrigió un caso real de auto-detección: el propio código fuente de un módulo
(que contiene los marcadores que busca, como datos) no debe aparecer como hallazgo cuando alguien
apunta un escaneo hacia el código de Pegazus.
