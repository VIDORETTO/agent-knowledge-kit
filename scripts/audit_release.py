"""Run the release-candidate audit for this clone."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docops.release_audit import audit_release  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tracked-only", action="store_true", help="audit only files known to the root Git index")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_release(args.root, tracked_only=args.tracked_only)
    print(result.to_json() if args.json else json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
