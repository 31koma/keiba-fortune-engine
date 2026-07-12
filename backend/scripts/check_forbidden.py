"""CI用: 禁止語フィルタ検査。

Mockデータの全組み合わせで鑑定文を実生成し、禁止語(正本
forbidden_expressions 由来)がゼロであることを実測確認する。
また triad が validation_required を維持していること(未確定の重みを
確定していないこと)も検査する。ヒットがあれば exit 1(マージ不可)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import STATE, app  # noqa: E402

COMBOS = [("H001", "J001", "R001"), ("H002", "J002", "R001"),
          ("H001", "J002", "R001"), ("H002", "J001", "R001")]


def main() -> int:
    failures = 0
    with TestClient(app) as client:
        ffilter = STATE.get("filter")
        if ffilter is None:
            print("NG: 知識ベースがdegradedのためフィルタ未初期化")
            return 1
        print(f"filter: {ffilter.status}")
        for horse, jockey, race in COMBOS:
            res = client.post("/v1/readings/horse-triad", json={
                "horse_id": horse, "jockey_id": jockey, "race_id": race})
            if res.status_code != 200:
                print(f"NG: triad {horse}x{jockey} -> HTTP {res.status_code}")
                failures += 1
                continue
            body = res.json()
            hits = ffilter.find(body["generated_interpretation"])
            if hits:
                print(f"NG: 禁止語検出 {horse}x{jockey}: {hits}")
                failures += 1
            else:
                print(f"OK: {horse}x{jockey} 禁止語ゼロ "
                      f"({len(body['generated_interpretation'])}文字)")
            if body.get("validation_status") != "validation_required":
                print(f"NG: {horse}x{jockey} validation_statusが"
                      f"validation_requiredではありません(重み未確定の原則違反)")
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
