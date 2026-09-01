from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from pegazus.core.db import SessionLocal, init_db
from pegazus.core.git_helpers import get_changed_files, get_staged_files
from pegazus.core.models import Scan, ScanStatus, Severity
from pegazus.core.orchestrator import run_scan
from pegazus.core.walker import is_pegazus_own_file, walk_project
from pegazus.modules.base import ModuleFinding, ScanContext
from pegazus.modules.registry import get_enabled_modules

app = typer.Typer(help="Proyecto-Pegazus: analisis local de proyectos.")

_BLOCKING_SEVERITIES = (Severity.CRITICAL, Severity.HIGH)
_HOOK_NAMES = ("pre-commit", "post-merge", "post-checkout")
HOOK_TEMPLATES_DIR = Path(__file__).resolve().parent / "hook_templates"
CI_TEMPLATES_DIR = Path(__file__).resolve().parent / "ci_templates"


@app.command()
def scan(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Ejecuta un escaneo completo sobre PATH y muestra los resultados en la terminal.

    Sale con codigo 1 si hay hallazgos de severidad alta/critica (util para
    el workflow de barrido periodico en CI, donde un exit distinto de cero
    es lo que hace fallar el job y avisar).
    """
    init_db()
    session = SessionLocal()
    try:
        scan_row = Scan(target_path=str(path), status=ScanStatus.PENDING)
        session.add(scan_row)
        session.commit()
        session.refresh(scan_row)

        run_scan(session, scan_row.id)
        session.refresh(scan_row)

        typer.echo(f"Escaneo #{scan_row.id} -> {scan_row.status.value}")
        typer.echo(f"Archivos analizados: {scan_row.files_scanned}")
        if scan_row.error_message:
            typer.echo(f"Error: {scan_row.error_message}")

        counts = scan_row.severity_counts()
        for severity, count in counts.items():
            if count:
                typer.echo(f"  {severity}: {count}")

        for finding in scan_row.findings:
            typer.echo(f"[{finding.severity.value.upper()}] {finding.title} - {finding.file_path}")

        blocking = sum(1 for f in scan_row.findings if f.severity in _BLOCKING_SEVERITIES)
    finally:
        session.close()

    if blocking:
        raise typer.Exit(code=1)


@app.command("scan-staged")
def scan_staged(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Analiza solo los archivos en stage (git diff --cached). Pensado para un hook pre-commit.

    No corre los chequeos de proyecto (historial de git, tareas de VS Code):
    esos son para un barrido periodico completo ('pegazus scan'), no para
    cada commit. Sale con codigo 1 si hay hallazgos de severidad alta/critica
    -- el hook pre-commit usa eso para bloquear el commit.
    """
    project_root = path.resolve()
    files = get_staged_files(project_root)
    if not files:
        typer.echo("No hay archivos en stage para analizar.")
        raise typer.Exit(code=0)

    _scan_files_and_report(project_root, files, action_label="Commit")


@app.command("scan-diff")
def scan_diff(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    from_ref: str = typer.Argument(...),
    to_ref: str = typer.Argument(...),
) -> None:
    """Analiza los archivos que cambiaron entre FROM_REF y TO_REF.

    Pensado para hooks post-merge/post-checkout (git pull / git clone). Git
    no permite bloquear un fast-forward antes de que los archivos toquen
    disco, asi que esto es deteccion inmediata + alerta fuerte, no
    prevencion: revisa los hallazgos antes de confiar en lo que se acaba de
    descargar.
    """
    project_root = path.resolve()
    files = get_changed_files(project_root, from_ref, to_ref)
    if not files:
        typer.echo("No hay archivos para analizar.")
        raise typer.Exit(code=0)

    _scan_files_and_report(project_root, files, action_label="Codigo recien descargado")


@app.command("safe-install")
def safe_install(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Instala dependencias con pnpm y analiza node_modules antes de aprobar sus scripts.

    A diferencia de npm (que ejecuta los scripts de lifecycle de todas las
    dependencias automaticamente), pnpm los deja pendientes de aprobacion por
    defecto. Flujo: 'pnpm install' (nada se ejecuta todavia) -> se analiza
    node_modules con los modulos habilitados -> si no hay hallazgos de
    severidad alta/critica, corre 'pnpm approve-builds --all' para ejecutar
    los scripts pendientes. Si los hay, NO se aprueban: para un paquete cuyo
    payload vive en su script de instalacion (p.ej. el gusano Shai-Hulud en
    npm), ese codigo nunca llega a correr.

    Esto NO protege contra un payload que se ejecuta al importar el paquete
    en vez de en un script de instalacion (asi operó parte del compromiso de
    chalk/debug en npm de 2025) -- para eso, el analisis de node_modules de
    abajo sigue corriendo igual y reporta lo que encuentre, aunque no pueda
    "prevenirlo" sin mas.

    Requiere pnpm en el PATH (ver README: corepack enable, o instalar pnpm
    por winget/scoop/npm).

    Limitacion conocida: si un paquete trae su propio node_modules anidado,
    ese subarbol se excluye del recorrido (igual que en un escaneo normal)
    para evitar profundidad excesiva.
    """
    project_root = path.resolve()
    if not (project_root / "package.json").exists():
        typer.echo(f"No se encontro package.json en '{project_root}'.", err=True)
        raise typer.Exit(code=1)

    typer.echo("Instalando dependencias (pnpm deja sus scripts pendientes de aprobacion)...")
    install = subprocess.run(
        ["pnpm", "install"], cwd=project_root, capture_output=True, text=True
    )
    typer.echo(install.stdout)
    if install.stderr:
        typer.echo(install.stderr, err=True)

    # pnpm sale con codigo 1 cuando hay scripts pendientes de aprobar -- ese
    # es el estado que buscamos (nada se ejecuto todavia), no un fallo real.
    scripts_pending = "ERR_PNPM_IGNORED_BUILDS" in install.stdout + install.stderr
    if install.returncode != 0 and not scripts_pending:
        typer.echo("Fallo 'pnpm install'.", err=True)
        raise typer.Exit(code=install.returncode)

    node_modules = project_root / "node_modules"
    if not node_modules.exists():
        typer.echo("No se genero node_modules; nada que analizar.")
        raise typer.Exit(code=0)

    typer.echo("Analizando dependencias instaladas antes de ejecutar sus scripts...")
    walk_result = walk_project(node_modules)
    findings = _scan_files(project_root, walk_result.files)
    blocking = [f for f in findings if f.severity in _BLOCKING_SEVERITIES]

    for finding in findings:
        typer.echo(f"[{finding.severity.value.upper()}] {finding.title} - {finding.file_path}")

    if blocking:
        typer.echo(
            f"\n{len(blocking)} hallazgo(s) de severidad alta/critica en node_modules. "
            f"Los scripts de instalacion NO se aprobaron. Revisa los hallazgos antes de "
            f"continuar (o corre 'pnpm approve-builds' manualmente, paquete por paquete, "
            f"si confias en el resto).",
            err=True,
        )
        raise typer.Exit(code=1)

    if not scripts_pending:
        typer.echo(f"\nSin hallazgos graves ({len(findings)} de baja severidad). Nada pendiente de aprobar.")
        raise typer.Exit(code=0)

    typer.echo(f"\nSin hallazgos graves ({len(findings)} de baja severidad). Aprobando scripts pendientes...")
    approve = subprocess.run(["pnpm", "approve-builds", "--all"], cwd=project_root)
    raise typer.Exit(code=approve.returncode)


@app.command("install-hooks")
def install_hooks(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    hooks_path: str = typer.Option(".githooks", help="Directorio (relativo al repo) donde instalar los hooks."),
    workflow: bool = typer.Option(
        True, help="Tambien escribir los workflows de GitHub Actions en .github/workflows/."
    ),
) -> None:
    """Instala los hooks de git de forma COMPARTIBLE, a diferencia de copiarlos a .git/hooks/.

    .git/hooks/ es local a cada maquina: nunca protege a nadie mas que a
    quien lo instalo. Este comando en cambio escribe los scripts en
    '<repo>/<hooks-path>/' (por defecto '.githooks/', un directorio normal
    que SI se puede comitear) y configura 'core.hooksPath' en ese repo para
    que git los use de ahi. Como '.githooks/' se versiona, cualquiera que
    clone el repo y corra este mismo comando (o
    'git config core.hooksPath .githooks' a mano) queda protegido tambien,
    no solo la maquina donde se corrio esto la primera vez.

    Por defecto tambien escribe dos workflows de GitHub Actions en
    '.github/workflows/' como respaldo del lado del servidor: cubren a
    quien comitea sin el hook local instalado, o lo salta con
    '--no-verify' -- algo que un hook local nunca puede evitar por si
    solo. Revisar el TODO de instalacion de 'pegazus' dentro de esos
    archivos antes de usarlos (no hay forma de adivinar donde va a estar
    publicado el paquete para tu organizacion).

    No hace falta volver a correr esto cuando se agregue un modulo de
    deteccion nuevo a Pegazus: los hooks y los workflows solo llaman a
    'pegazus scan-*', que recorre todos los modulos registrados -- alcanza
    con actualizar el paquete 'pegazus' instalado en cada maquina/runner.
    """
    repo_root = path.resolve()
    if not (repo_root / ".git").exists():
        typer.echo(f"'{repo_root}' no parece ser la raiz de un repositorio git (no hay .git).", err=True)
        raise typer.Exit(code=1)

    hooks_dir = repo_root / hooks_path
    hooks_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Escribiendo hooks en {hooks_path}/:")
    for name in _HOOK_NAMES:
        source = HOOK_TEMPLATES_DIR / name
        dest = hooks_dir / name
        dest.write_bytes(source.read_bytes())
        dest.chmod(0o755)
        typer.echo(f"  {dest.relative_to(repo_root)}")

    config = subprocess.run(["git", "config", "core.hooksPath", hooks_path], cwd=repo_root)
    if config.returncode != 0:
        typer.echo("No se pudo configurar core.hooksPath.", err=True)
        raise typer.Exit(code=config.returncode)
    typer.echo(f"core.hooksPath -> {hooks_path} (config local de este repo)")

    if workflow:
        workflows_dir = repo_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        typer.echo("Escribiendo workflows en .github/workflows/:")
        for source in sorted(CI_TEMPLATES_DIR.glob("*.yml")):
            dest = workflows_dir / source.name
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            typer.echo(f"  {dest.relative_to(repo_root)}")

    hook_list = " ".join(f"{hooks_path}/{name}" for name in _HOOK_NAMES)
    typer.echo(
        f"\nListo. '{hooks_path}/' es un directorio normal: comitealo (git add {hooks_path} "
        f"&& git commit) para que proteja a todo el equipo, no solo esta maquina. Quien "
        f"clone el repo debe correr 'pegazus install-hooks .' una vez (o "
        f"'git config core.hooksPath {hooks_path}' a mano) para activarlo localmente -- "
        f"eso es config local de git, no viaja con el commit.\n"
        f"En Windows: NTFS no tiene bit ejecutable real, asi que despues del primer commit "
        f"conviene forzarlo con 'git update-index --chmod=+x {hook_list}' y comitear eso "
        f"tambien, para que colaboradores en Linux/Mac lo reciban ya ejecutable."
    )


def _scan_files(project_root: Path, files: list[Path]) -> list[ModuleFinding]:
    modules = get_enabled_modules()
    context = ScanContext(project_root=project_root, scan_id=0)

    findings: list[ModuleFinding] = []
    for file_path in files:
        if is_pegazus_own_file(file_path):
            continue
        for module in modules:
            findings.extend(module.scan_file(file_path, context))
    return findings


def _scan_files_and_report(project_root: Path, files: list[Path], *, action_label: str) -> None:
    findings = _scan_files(project_root, files)
    for finding in findings:
        typer.echo(f"[{finding.severity.value.upper()}] {finding.title} - {finding.file_path}")

    blocking = [f for f in findings if f.severity in _BLOCKING_SEVERITIES]
    if blocking:
        typer.echo(
            f"\n{action_label}: {len(blocking)} hallazgo(s) de severidad alta/critica "
            f"en {len(files)} archivo(s) analizados.",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"\n{len(findings)} hallazgo(s) de baja severidad en {len(files)} archivo(s) analizados.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
