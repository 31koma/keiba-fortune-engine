"""シンクロエンジン: 今日のシンクロ度(4者調和+集合意識)の決定的計算。

規則・重み・文言は knowledge/proposals/synchro_v0.json(正本v1.3収録候補、
app_hypothesis)から読む。コードは計算手順のみを持ち、意味を持たない。
オッズ=集合意識(市場に集まる意識の総量)の近似、という捉え方自体が仮説であり
validation_required。勝率・的中率・結果予測を表すものではない。
"""
import json
import math
from datetime import date
from pathlib import Path

from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO
from app.domain.engine.numerology import Numerology
from app.domain.engine.zodiac import Zodiac
from app.knowledge.loader import KnowledgeStore

PROPOSAL_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "proposals" / "synchro_v0.json"


def load_rules(path: Path | None = None) -> dict:
    p = path or PROPOSAL_PATH
    return json.loads(p.read_text(encoding="utf-8"))


class SynchroEngine:
    def __init__(self, kb: KnowledgeStore, num: Numerology, zod: Zodiac,
                 rules: dict | None = None):
        self.kb = kb
        self.num = num
        self.zod = zod
        self.rules = rules or load_rules()

    # ---------- 部品 ----------
    def _norm13(self, raw: float) -> float:
        """1..3スコアを0..10へ正規化(規則components.harmony.normalize)。"""
        return (raw - 1.0) / 2.0 * 10.0

    def _personal_day(self, birth: date, target: date) -> int:
        py = self.num.personal_year(birth, target.year)["value"]
        pm = self.num.personal_month(py, target.month)["value"]
        return self.num.personal_day(pm, target.day)["value"]

    def harmony(self, horse: HorseDTO, jockey: JockeyDTO) -> dict:
        hs = self.zod.sign_for_date(horse.birth_date)
        js = self.zod.sign_for_date(jockey.birth_date)
        zc = self.zod.combined_score(hs["sign_id"], js["sign_id"],
                                     hs["element"], js["element"])
        h_lp = self.num.life_path(horse.birth_date)["value"]
        j_lp = self.num.life_path(jockey.birth_date)["value"]
        gc = self.num.group_compat(self.kb, h_lp, j_lp)
        score = round((self._norm13(zc["score"]) + self._norm13(gc["score"])) / 2, 2)
        return {"score": score, "zodiac_combined": zc["score"],
                "group": gc["condition"], "group_label": gc["label_ja"]}

    def day_flow(self, horse: HorseDTO, target: date) -> dict:
        pd = self._personal_day(horse.birth_date, target)
        ud = self.num.universal_day(target)["value"]
        m = self.rules["components"]["day_flow"]["map"]
        if pd == ud:
            key = "same_number"
        elif self.num.group_of(self.kb, pd) == self.num.group_of(self.kb, ud):
            key = "same_group"
        else:
            key = "different"
        return {"score": m[key], "condition": key, "personal_day": pd, "universal_day": ud}

    def user_resonance(self, horse: HorseDTO, user_birth: date, target: date) -> dict:
        h_pd = self._personal_day(horse.birth_date, target)
        u_pd = self._personal_day(user_birth, target)
        ud = self.num.universal_day(target)["value"]
        m = self.rules["components"]["user_resonance"]["map"]
        if u_pd == h_pd:
            key = "same_number"
        elif self.num.group_of(self.kb, u_pd) == self.num.group_of(self.kb, h_pd):
            key = "same_group"
        elif self.num.group_of(self.kb, u_pd) == self.num.group_of(self.kb, ud):
            key = "universal_match"
        else:
            key = "different"
        return {"score": m[key], "condition": key,
                "user_personal_day": u_pd, "horse_personal_day": h_pd}

    def collective(self, win_odds: float | None) -> dict:
        """オッズ→集合意識の注目度(0..10)。オッズ未取得は中立5.0(注目情報なし)。"""
        c = self.rules["components"]["collective"]
        if win_odds is None or win_odds <= 0:
            return {"score": 5.0, "support_share": None, "win_odds": None,
                    "note": "オッズ未取得のため中立値"}
        s = max(c["clip_min"], min(c["clip_max"], c["takeout_assumption"] / win_odds))
        att = max(0.0, min(10.0, 5.0 * math.log10(100.0 * s)))
        return {"score": round(att, 2), "support_share": round(s, 4), "win_odds": win_odds}

    # ---------- 合成 ----------
    def compute(self, horse: HorseDTO, jockey: JockeyDTO, race: RaceDTO,
                target: date, win_odds: float | None,
                user_birth: date | None = None) -> dict:
        har = self.harmony(horse, jockey)
        day = self.day_flow(horse, target)
        col = self.collective(win_odds)
        comps = {"harmony": har, "day_flow": day, "collective": col}

        if user_birth is not None:
            usr = self.user_resonance(horse, user_birth, target)
            comps["user_resonance"] = usr
            w = self.rules["weights"]["with_user"]
            flow_parts = {"harmony": har["score"], "day_flow": day["score"],
                          "user_resonance": usr["score"]}
        else:
            w = self.rules["weights"]["without_user"]
            flow_parts = {"harmony": har["score"], "day_flow": day["score"]}

        total = sum(comps[k]["score"] * w[k] for k in w)
        flow_w = {k: w[k] for k in flow_parts}
        flow = sum(flow_parts[k] * flow_w[k] for k in flow_w) / sum(flow_w.values())
        score = round(min(10.0, total), 1)
        flow = round(flow, 2)

        th = self.rules["patterns"]["thresholds"]
        att = col["score"]
        if flow >= th["flow_high"] and att >= th["attention_high"]:
            ptype = "resonance"
        elif flow >= th["flow_high"] and att < th["attention_low"]:
            ptype = "hidden"
        elif flow < th["flow_low"] and att >= th["attention_high"]:
            ptype = "heat"
        else:
            ptype = "quiet"
        pinfo = self.rules["patterns"]["types"][ptype]

        band = next(b for b in self.rules["score_bands"] if score >= b["min"])
        return {
            "score": score,
            "tier": band["tier"],
            "label": band["label_ja"],
            "flow": flow,
            "pattern": {"type": ptype, "label_ja": pinfo["label_ja"], "line": pinfo["line"]},
            "components": comps,
            "weights": w,
            "rule": "synchro_score_v0(app_hypothesis)",
            "hypothesis_status": self.rules["meta"]["status"],
            "validation_status": self.rules["meta"]["validation"],
        }
