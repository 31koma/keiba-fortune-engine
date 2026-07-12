"""CI用: OpenAPI生成確認。

/openapi.json が生成でき、OpenAPI 3.1系で必須4エンドポイントを含むことを検証。
成果物として openapi.json をリポジトリルートに書き出す(CIアーティファクト用)。
失敗時は exit 1(マージ不可)。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

REQUIRED_PATHS = ["/health", "/v1/profile", "/v1/day-fortune",
                  "/v1/readings/horse-triad"]


def main() -> int:
    with TestClient(app) as client:
        res = client.get("/openapi.json")
        if res.status_code != 200:
            print(f"NG: /openapi.json -> HTTP {res.status_code}")
            return 1
        spec = res.json()
    version = spec.get("openapi", "")
    if not version.startswith("3.1"):
        print(f"NG: OpenAPIバージョンが3.1系ではありません: {version}")
        return 1
    missing = [p for p in REQUIRED_PATHS if p not in spec.get("paths", {})]
    if missing:
        print(f"NG: 必須パスが不足: {missing}")
        return 1
    out = Path(__file__).resolve().parents[2] / "openapi.json"
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: OpenAPI {version} / paths={len(spec['paths'])} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
