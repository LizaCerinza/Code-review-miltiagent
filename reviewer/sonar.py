"""Lee los issues que Sonar ya reportó en el PR, para que el agente de seguridad no los repita."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


def read_project_key(workspace: Path) -> str | None:
    """Toma `sonar.projectKey` de sonar-project.properties, si existe."""
    props = workspace / "sonar-project.properties"
    if not props.is_file():
        return None
    for line in props.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("sonar.projectKey="):
            return line.split("=", 1)[1].strip() or None
    return None


def fetch_pr_issues(
    host: str, token: str, project_key: str, pr: int, client: httpx.Client | None = None
) -> list[dict] | None:
    """Issues abiertos del PR, o None si Sonar no respondió (la revisión continúa igual)."""
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.get(
            f"{host.rstrip('/')}/api/issues/search",
            params={
                "componentKeys": project_key,
                "pullRequest": str(pr),
                "resolved": "false",
                "ps": "500",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        issues = response.json().get("issues", [])
    except (httpx.HTTPError, ValueError) as error:
        log.warning("No se pudieron leer los issues de Sonar: %s", error)
        return None
    finally:
        if client is None:
            http.close()

    prefix = f"{project_key}:"
    return [
        {
            "rule": issue.get("rule"),
            "severity": issue.get("severity"),
            "type": issue.get("type"),
            "file": str(issue.get("component", "")).removeprefix(prefix),
            "line": issue.get("line"),
            "message": issue.get("message"),
        }
        for issue in issues
    ]
