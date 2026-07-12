"""CI用: 知識ベース整合チェック(起動時検証と同一ロジックを単体実行)。
サイズ/SHA-256/JSON構文/必須キー/出典ID/ステータス語彙/day_theme鏡写しを検証し、
degraded なら exit 1(マージ不可)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.knowledge.loader import load_knowledge  # noqa: E402


def main() -> int:
    kb = load_knowledge(settings.kb_dir, settings.manifest_md)
    r = kb.report
    print(f"knowledge base: {r.status} (version={r.version}, "
          f"loaded={r.loaded_file_count}/{len(r.files)})")
    for f in r.files:
        mark = "OK " if f.ok else "NG "
        print(f"  {mark}{f.name}  {f.actual_size}/{f.actual_sha16}"
              + (f"  <- {f.error}" if f.error else ""))
    if r.problems:
        print("problems:")
        for p in r.problems:
            print(f"  - {p}")
    return 0 if r.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
