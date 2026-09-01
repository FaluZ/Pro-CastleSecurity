from __future__ import annotations

import httpx

from pegazus.core.config import settings


class JsBridgeUnavailable(RuntimeError):
    """El servicio analyzer-js no esta disponible o no respondio correctamente."""


def analyze_file(file_path: str, timeout: float = 5.0) -> list[dict]:
    """Envia un archivo al servicio analyzer-js (Node) para analisis de AST de JavaScript.

    Ningun modulo lo usa todavia: el MVP solo cubre malware generico, que opera
    sobre bytes crudos. Este cliente es el punto de extension que usaran los
    modulos de EtherHiding y Contagious Interview, que necesitan un parser de
    JS real (acorn/@babel del lado de analyzer-js) en vez de regex en Python.
    """
    try:
        response = httpx.post(
            f"{settings.jsbridge_url}/analyze",
            json={"filePath": file_path},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise JsBridgeUnavailable(str(exc)) from exc

    return response.json().get("findings", [])
