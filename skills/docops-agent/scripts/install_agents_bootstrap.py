"""Install the DOCOPS persistent-knowledge rule in a project's AGENTS.md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if (_REPO_ROOT / "docops").is_dir() and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from docops import agent_skill as _agent_skill  # type: ignore[import-not-found]

    BLOCK = _agent_skill.BOOTSTRAP_BLOCK
    MARKER = _agent_skill.BOOTSTRAP_MARKER
    _shared_install = _agent_skill.install_agents_bootstrap
except ImportError:
    _shared_install = None
    MARKER = "DOCOPS-PERSISTENT-KNOWLEDGE"
    BLOCK = """## DOCOPS-PERSISTENT-KNOWLEDGE

Quando uma tarefa envolver documentação persistente, memória do projeto,
Agent Skills, RAG, fontes, citações ou aprendizado de conversas, leia primeiro
`skills/docops-agent/SKILL.md` (ou o caminho equivalente instalado no host).
Use essa skill para decidir entre conhecimento conceitual e busca factual,
preservar proveniência e seguir o ciclo seguro de atualização. Se outras skills
`rag-*` ou de domínio estiverem instaladas, siga a precedência em
`skills/docops-agent/references/skill-interoperability.md`. Depois leia as
regras específicas deste projeto e só então opere.
"""


def install(root: Path, *, check: bool = False) -> dict[str, str | bool]:
    """Ensure the marker block exists without overwriting existing instructions."""

    if _shared_install is not None:
        return _shared_install(root, check=check)

    project_root = root.expanduser().resolve()
    target = project_root / "AGENTS.md"
    if target.is_symlink():
        raise ValueError("AGENTS.md must not be a symbolic link")
    if target.exists() and not target.is_file():
        raise ValueError("AGENTS.md must be a regular file")
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if MARKER in current:
        return {"ok": True, "changed": False, "status": "present"}
    if check:
        return {"ok": False, "changed": False, "status": "missing"}
    prefix = current.rstrip()
    updated = f"{prefix}\n\n{BLOCK}" if prefix else f"{BLOCK}"
    target.write_text(updated.rstrip() + "\n", encoding="utf-8", newline="\n")
    return {"ok": True, "changed": True, "status": "installed"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="target project root")
    parser.add_argument("--check", action="store_true", help="do not write; fail if the marker is absent")
    args = parser.parse_args(argv)
    try:
        result = install(args.root, check=args.check)
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
