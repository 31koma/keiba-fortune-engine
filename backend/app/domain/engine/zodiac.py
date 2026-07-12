"""星座の決定的計算。区分日・相性表・重みは正本(zodiac_core.json)から取得。

エフェメリス厳密判定は未導入(on_hold)。正本 default_policy.boundary_handling
「境界日(±1日)はboundary_flagを立て、厳密判定は天文暦で行う」に従い、
境界±1日は boundary_flag=True を返すのみで断定しない。
"""
import re
from datetime import date, timedelta

from app.core.errors import KnowledgeGapError
from app.knowledge.loader import KnowledgeStore


class Zodiac:
    def __init__(self, kb: KnowledgeStore):
        zc = kb.zodiac
        self.signs: list[dict] = zc["signs"]
        self.elements: dict = zc["elements"]
        self.compat: dict = zc["compatibility"]
        self.policy: dict = zc["default_policy"]

    def _md(self, d: date) -> str:
        return f"{d.month:02d}-{d.day:02d}"

    def sign_for_date(self, d: date) -> dict:
        md = self._md(d)
        found = None
        for s in self.signs:
            start, end = s["start_md"], s["end_md"]
            if start <= end:
                if start <= md <= end:
                    found = s
                    break
            else:  # 年跨ぎ(山羊座)
                if md >= start or md <= end:
                    found = s
                    break
        if found is None:
            raise KnowledgeGapError(f"zodiac_core.signs で日付 {md} が未カバー")
        # 境界±1日(正本 boundary_handling)
        boundaries = {s["start_md"] for s in self.signs} | {s["end_md"] for s in self.signs}
        near = any(self._md(d + timedelta(days=k)) in boundaries for k in (-1, 0, 1))
        return {"sign_id": found["id"], "name_ja": found["name_ja"],
                "name_en": found["name_en"], "element": found["element"],
                "modality": found["modality"], "boundary_flag": near,
                "boundary_note": self.policy["boundary_handling"] if near else None,
                "rule": "zodiac.sun_sign(tropical)", "source_ids": found.get("source_ids", [])}

    # --- distance法(正本 compatibility.distance_method) ---
    def distance_compat(self, sign_a: int, sign_b: int) -> dict:
        dm = self.compat["distance_method"]
        dist = min(abs(sign_a - sign_b), 12 - abs(sign_a - sign_b))
        info = dm["distance_table"].get(str(dist))
        if info is None:
            raise KnowledgeGapError(f"distance_table に {dist} が未定義")
        return {"distance": dist, **info, "status": dm["status"],
                "source_ids": dm["source_ids"], "rule": "zodiac.distance_method"}

    # --- element法(正本 compatibility.element_method: 同元素=3, harmonious=3, tense=1) ---
    def element_compat(self, elem_a: str, elem_b: str) -> dict:
        em = self.compat["element_method"]
        ea = self.elements[elem_a]
        if elem_a == elem_b or elem_b in ea["harmonious_with"]:
            score = 3
        elif elem_b in ea["tense_with"]:
            score = 1
        else:
            raise KnowledgeGapError(f"elements 相互関係が未定義: {elem_a}×{elem_b}")
        return {"elements": [elem_a, elem_b], "score": score, "status": em["status"],
                "source_ids": em["source_ids"], "rule": "zodiac.element_method"}

    # --- 合成スコア(正本 combined_score。重みは正本のalgorithm文字列から抽出) ---
    def combined_score(self, sign_a: int, sign_b: int, elem_a: str, elem_b: str) -> dict:
        cs = self.compat["combined_score"]
        weights = re.findall(r"\(([\d.]+)\)", cs["algorithm"])
        if len(weights) < 2:
            raise KnowledgeGapError("combined_score.algorithm から重みを抽出できません")
        wd, we = float(weights[0]), float(weights[1])
        d = self.distance_compat(sign_a, sign_b)
        e = self.element_compat(elem_a, elem_b)
        return {"score": round(wd * d["score"] + we * e["score"], 2),
                "weights": {"distance": wd, "element": we},
                "components": {"distance": d, "element": e},
                "status": cs["status"], "rule": "zodiac.combined_score"}
