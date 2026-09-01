from __future__ import annotations

from pathlib import Path

from pegazus.modules.etherhiding.structural import check_long_line, check_whitespace_gap


def test_long_line_in_vite_config_is_flagged() -> None:
    data = b"export default {}\n" + b"x" * 500 + b";\n"

    findings = check_long_line(Path("vite.config.js"), data)

    assert len(findings) == 1
    assert findings[0].severity.value == "medium"


def test_short_lines_in_vite_config_are_not_flagged() -> None:
    data = b"export default {\n  plugins: [],\n}\n"

    findings = check_long_line(Path("vite.config.js"), data)

    assert findings == []


def test_long_line_in_unrelated_file_is_ignored() -> None:
    data = b"x" * 500

    findings = check_long_line(Path("data.txt"), data)

    assert findings == []


def test_electron_entry_in_resources_app_is_checked() -> None:
    data = b"x" * 500

    findings = check_long_line(Path("app/resources/app/out/main/index.js"), data)

    assert len(findings) == 1


def test_ordinary_index_js_is_not_checked() -> None:
    data = b"x" * 500

    findings = check_long_line(Path("src/index.js"), data)

    assert findings == []


def test_whitespace_gap_after_closing_paren_is_flagged() -> None:
    data = b"module.exports = defineConfig({\n  plugins: [react()]\n});" + b" " * 60 + b"eval(1)\n"

    findings = check_whitespace_gap(Path("vite.config.js"), data)

    assert len(findings) == 1
    assert findings[0].severity.value == "high"


def test_normal_code_has_no_gap_finding() -> None:
    data = b"module.exports = defineConfig({\n  plugins: [react()]\n});\n"

    findings = check_whitespace_gap(Path("vite.config.js"), data)

    assert findings == []


def test_gap_check_ignores_unrelated_extensions() -> None:
    data = b"});" + b" " * 60 + b"eval(1)\n"

    findings = check_whitespace_gap(Path("notes.txt"), data)

    assert findings == []
