"""Publicación idempotente de la revisión en el PR."""

from __future__ import annotations

import logging
import re

import httpx

from .diff import ChangedFile, commentable_lines
from .github import GitHubClient
from .models import ReviewResult
from .report import SUMMARY_MARKER, render_inline, render_summary

log = logging.getLogger(__name__)

_FINGERPRINT_RE = re.compile(r"<!-- ai-review:fp=([0-9a-f]+) -->")


def publish(
    gh: GitHubClient, pr: int, head_sha: str, result: ReviewResult, files: list[ChangedFile]
) -> int:
    """Publica el resumen y los comentarios inline nuevos. Devuelve cuántos inline publicó."""
    upsert_summary(gh, pr, render_summary(result))

    lines_by_file = {f.path: commentable_lines(f.patch) for f in files}
    already_posted = {
        fp
        for comment in gh.list_review_comments(pr)
        for fp in _FINGERPRINT_RE.findall(comment.get("body") or "")
    }
    comments = [
        {"path": f.file, "line": f.line, "side": "RIGHT", "body": render_inline(f)}
        for f in result.findings
        if f.line and f.line in lines_by_file.get(f.file, set())
        and f.fingerprint not in already_posted
    ]
    if not comments:
        return 0
    try:
        gh.create_review(pr, head_sha, "Comentarios del code review multiagente.", comments)
    except httpx.HTTPStatusError as error:
        if error.response.status_code != 422:
            raise
        # GitHub rechazó alguna línea: el resumen ya tiene todos los hallazgos.
        log.warning("GitHub rechazó los comentarios inline (422); solo se publicó el resumen.")
        return 0
    return len(comments)


def upsert_summary(gh: GitHubClient, pr: int, body: str) -> None:
    for comment in gh.list_issue_comments(pr):
        if SUMMARY_MARKER in (comment.get("body") or ""):
            gh.update_issue_comment(comment["id"], body)
            return
    gh.create_issue_comment(pr, body)
