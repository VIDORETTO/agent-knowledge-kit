"""Discovery and safe bootstrap helpers for the first-party DOCOPS skill."""

from __future__ import annotations

import os
import sys
import sysconfig
from pathlib import Path
from typing import Final

SKILL_NAME = "docops-agent"
BOOTSTRAP_MARKER = "DOCOPS-PERSISTENT-KNOWLEDGE"
BOOTSTRAP_BLOCK = """## DOCOPS-PERSISTENT-KNOWLEDGE

Quando uma tarefa envolver documentação persistente, memória do projeto,
Agent Skills, RAG, fontes, citações ou aprendizado de conversas, leia primeiro
`skills/docops-agent/SKILL.md` (ou o caminho equivalente instalado no host).
Use essa skill para decidir entre conhecimento conceitual e busca factual,
preservar proveniência e seguir o ciclo seguro de atualização. Se outras skills
`rag-*` ou de domínio estiverem instaladas, siga a precedência em
`skills/docops-agent/references/skill-interoperability.md`. Depois leia as
regras específicas deste projeto e só então opere.
"""

_SKILL_RELATIVE: Final[Path] = Path("skills") / SKILL_NAME
_REQUIRED_FILES: Final[tuple[Path, ...]] = (
    Path("SKILL.md"),
    Path("agents") / "openai.yaml",
    Path("references") / "agents-bootstrap.md",
    Path("references") / "command-cards.md",
    Path("references") / "skill-interoperability.md",
    Path("references") / "scheduler-runbooks.md",
)


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _usable(path: Path) -> bool:
    """Return whether a candidate is a complete, non-linked skill tree."""

    if path.is_symlink() or not path.is_dir():
        return False
    return all(_regular_file(path / relative) for relative in _REQUIRED_FILES)


def skill_candidates() -> tuple[Path, ...]:
    """Return deterministic checkout and installation locations."""

    candidates: list[Path] = []
    configured = os.environ.get("DOCOPS_AGENT_SKILL_ROOT", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())

    module_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        (
            module_root / _SKILL_RELATIVE,
            module_root / "share" / "docops" / _SKILL_RELATIVE,
            Path.cwd() / _SKILL_RELATIVE,
        )
    )
    data_root = Path(sysconfig.get_path("data") or sys.prefix)
    candidates.extend(
        (
            data_root / "share" / "docops" / _SKILL_RELATIVE,
            Path(sys.prefix) / "share" / "docops" / _SKILL_RELATIVE,
        )
    )

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate.is_symlink():
            continue
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return tuple(unique)


def find_skill_root(explicit: Path | str | None = None) -> Path:
    """Find a complete first-party skill, preferring an explicit location."""

    candidates = (Path(explicit).expanduser(),) if explicit is not None else skill_candidates()
    for candidate in candidates:
        if candidate.is_symlink():
            continue
        resolved = candidate.resolve()
        if _usable(resolved):
            return resolved
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"first-party skill {SKILL_NAME!r} not found; searched: {searched}")


def skill_metadata(path: Path | str | None = None) -> dict[str, str]:
    """Return stable metadata for CLI and external harnesses."""

    root = find_skill_root(path)
    return {"name": SKILL_NAME, "path": str(root), "entrypoint": str(root / "SKILL.md")}


def install_agents_bootstrap(root: Path | str, *, check: bool = False) -> dict[str, str | bool]:
    """Install the routing rule without overwriting project instructions."""

    raw_root = Path(root).expanduser()
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise ValueError("bootstrap root must be a regular directory")
    project_root = raw_root.resolve()
    target = project_root / "AGENTS.md"
    if target.is_symlink():
        raise ValueError("AGENTS.md must not be a symbolic link")
    if target.exists() and not target.is_file():
        raise ValueError("AGENTS.md must be a regular file")
    try:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
    except (OSError, UnicodeError) as exc:
        raise ValueError("AGENTS.md could not be read") from exc
    if BOOTSTRAP_MARKER in current:
        return {"ok": True, "changed": False, "status": "present"}
    if check:
        return {"ok": False, "changed": False, "status": "missing"}
    prefix = current.rstrip()
    updated = f"{prefix}\n\n{BOOTSTRAP_BLOCK}" if prefix else BOOTSTRAP_BLOCK
    try:
        target.write_text(updated.rstrip() + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        raise ValueError("AGENTS.md could not be written") from exc
    return {"ok": True, "changed": True, "status": "installed"}


__all__ = [
    "BOOTSTRAP_BLOCK",
    "BOOTSTRAP_MARKER",
    "SKILL_NAME",
    "find_skill_root",
    "install_agents_bootstrap",
    "skill_candidates",
    "skill_metadata",
]
