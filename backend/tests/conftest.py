"""pytest設定: 知識ベースの解決。

- 環境変数 KEIBA_KB_DIR / KEIBA_MANIFEST_MD が有効(実在)ならそれを使う
  (ローカル開発では実正本、CIでは事前生成済みMockを指す)
- 未設定なら Mock知識ベースを一時生成して使う(CI・クリーン環境用)

正本(Google Drive)はリポジトリに含めない。Mockは構造のみ正本と同一の
テスト用フィクスチャであり、占術知識としての意味を持たない。
"""
import importlib.util
import os
import tempfile
from pathlib import Path


def _load_builder():
    p = Path(__file__).parent / "mock_kb.py"
    spec = importlib.util.spec_from_file_location("mock_kb", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_mock_kb


kb_dir = os.environ.get("KEIBA_KB_DIR")
manifest = os.environ.get("KEIBA_MANIFEST_MD")
if not (kb_dir and Path(kb_dir).is_dir() and manifest and Path(manifest).is_file()):
    tmp = Path(tempfile.mkdtemp(prefix="mock_kb_")) / "kb"
    m = _load_builder()(tmp)
    os.environ["KEIBA_KB_DIR"] = str(tmp)
    os.environ["KEIBA_MANIFEST_MD"] = str(m)
    os.environ.setdefault("KEIBA_DATABASE_URL", f"sqlite:///{tmp}/test.db")
