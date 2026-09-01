from __future__ import annotations

from pathlib import Path

from pegazus.modules.contagious_interview.vscode_tasks import check_autorun_tasks


def _write_vscode(tmp_path: Path, tasks: str, settings: str) -> Path:
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "tasks.json").write_text(tasks, encoding="utf-8")
    (vscode_dir / "settings.json").write_text(settings, encoding="utf-8")
    return tmp_path


def test_autorun_task_with_allowed_setting_is_flagged(tmp_path: Path) -> None:
    tasks = '{"tasks": [{"label": "setup", "runOptions": {"runOn": "folderOpen"}}]}'
    settings = '{"task.allowAutomaticTasks": "on"}'
    project_root = _write_vscode(tmp_path, tasks, settings)

    findings = check_autorun_tasks(project_root)

    assert len(findings) == 1
    assert findings[0].severity.value == "high"


def test_hidden_autorun_task_is_critical(tmp_path: Path) -> None:
    tasks = (
        '{"tasks": [{"label": "setup", "runOptions": {"runOn": "folderOpen"}, '
        '"presentation": {"reveal": "never", "hide": true}}]}'
    )
    settings = '{"task.allowAutomaticTasks": true}'
    project_root = _write_vscode(tmp_path, tasks, settings)

    findings = check_autorun_tasks(project_root)

    assert len(findings) == 1
    assert findings[0].severity.value == "critical"


def test_autorun_without_allow_setting_is_not_flagged(tmp_path: Path) -> None:
    tasks = '{"tasks": [{"label": "setup", "runOptions": {"runOn": "folderOpen"}}]}'
    settings = "{}"
    project_root = _write_vscode(tmp_path, tasks, settings)

    findings = check_autorun_tasks(project_root)

    assert findings == []


def test_missing_vscode_dir_is_not_flagged(tmp_path: Path) -> None:
    findings = check_autorun_tasks(tmp_path)

    assert findings == []
