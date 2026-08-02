"""熱量エンジン v1 — 「今日いちばん熱い物語」の算出。

heat = oshi + 地運補正 + (天運相性 - 4) × 0.5

規則・重み・文言は knowledge/proposals/heat_v1.json(app_hypothesis / validation_required)。
知識(干支の関係・五行の生剋・方位の配当)は正本v1.3の sizhu_day_pillar.json と
racecourse_geography.json から読む。**知識も重みもコードに書かない。**

v0からの変更(run6の実測に基づく):
- 人気とのギャップ点をスコアから完全に除外した(オッズ由来の成分を混ぜない)。
  「設計図上位なのに人気が薄い」は story chip(隠れ熱)として物語にのみ使う。
- 共鳴(あなた×馬)は引き続きスコアに入れない(客観・全員共通)。

勝率・的中率・レース結果の予測を表すものではない。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

PROPOSAL_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "proposals" / "heat_v1.json"


def load_rules() -> dict:
    return json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 日柱(暦の算術)

_STEM_ORDER = "甲乙丙丁戊己庚辛壬癸"
_BRANCH_ORDER = "子丑寅卯辰巳午未申酉戌亥"


def _jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def day_pillar(date_iso: str) -> str:
    """YYYY-MM-DD → 日柱(例: 戊申)。sizhu_day_pillar.json の calculation 規則。"""
    y, m, d = (int(x) for x in date_iso[:10].split("-"))
    idx = (_jdn(y, m, d) + 49) % 60
    return _STEM_ORDER[idx % 10] + _BRANCH_ORDER[idx % 12]


def verify_anchors(sizhu: dict) -> None:
    """正本のアンカー2点を検算。不一致なら例外(黙ってフォールバックしない)。"""
    for anchor in sizhu["calculation"]["verification_anchors"]:
        got = day_pillar(anchor["date"])
        if got != anchor["expected"]:
            raise ValueError(
                f"day_pillar anchor mismatch: {anchor['date']} expected {anchor['expected']} got {got}")


# ---------------------------------------------------------------- 五行・干支の関係(知識は正本から)

class _Knowledge:
    """sizhu_day_pillar.json / racecourse_geography.json からの読み取り専用ビュー。"""

    def __init__(self, sizhu: dict, geography: dict):
        self.sizhu = sizhu
        self.geography = geography
        stems = sizhu["stems"]  # keyは"1".."10"
        self.stem_element = {v["name_ja"]: v["element"] for v in stems.values()}
        self.generating = sizhu["five_elements"]["generating"]
        self.controlling = sizhu["five_elements"]["controlling"]
        comb = sizhu["combinations"]
        self.stem_union = {frozenset(p[:2]) for p in comb["stem_union"]["pairs"]}
        self.branch_union = {frozenset(p) for p in comb["branch_union"]["pairs"]}
        self.branch_clash = {frozenset(p) for p in comb["branch_clash"]["pairs"]}
        self.trinities = [set(s[:3]) for s in comb["branch_trinity"]["sets"]]


# ---------------------------------------------------------------- 地運

def venue_bearing_deg(ref_lat: float, ref_lon: float, lat: float, lon: float) -> float:
    """球面上の初期方位角(真北0度・時計回り)。racecourse_geography.bearing_rule。"""
    la1, la2 = math.radians(ref_lat), math.radians(lat)
    dlon = math.radians(lon - ref_lon)
    theta = math.atan2(
        math.sin(dlon) * math.cos(la2),
        math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlon))
    return (math.degrees(theta) + 360.0) % 360.0


def _distance_km(ref_lat: float, ref_lon: float, lat: float, lon: float) -> float:
    la1, la2 = math.radians(ref_lat), math.radians(lat)
    dphi = math.radians(lat - ref_lat)
    dlmb = math.radians(lon - ref_lon)
    a = math.sin(dphi / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlmb / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_SECTORS = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]


def bearing_to_sector(deg: float) -> str:
    """8方位に丸める(北=337.5〜22.5、以降45度刻み)。"""
    return _SECTORS[int(((deg + 22.5) % 360) // 45)]


def venue_element(geography: dict, course_key: str, ref_lat: float | None = None,
                  ref_lon: float | None = None) -> str:
    """競馬場の五行。基準点未指定なら fixed(日本経緯度原点)を使う。"""
    rule = geography["bearing_rule"]
    if ref_lat is None or ref_lon is None:
        fixed = rule["reference_point"]["modes"]["fixed"]
        ref_lat, ref_lon = fixed["lat"], fixed["lon"]
    course = geography["courses"][course_key]
    emap = geography["element_assignment"]["map"]
    if _distance_km(ref_lat, ref_lon, course["lat"], course["lon"]) < 50.0:
        return emap["同じ場"]
    return emap[bearing_to_sector(venue_bearing_deg(ref_lat, ref_lon, course["lat"], course["lon"]))]


def chi_relation(kn: _Knowledge, horse_stem: str, venue_el: str) -> str:
    """馬の日干の五行×舞台の五行 → 関係キー(chi_adjustmentsのキー)。"""
    h = kn.stem_element[horse_stem]
    if h == venue_el:
        return "same"
    if kn.generating[venue_el] == h:
        return "venue_generates_horse"
    if kn.generating[h] == venue_el:
        return "horse_generates_venue"
    if kn.controlling[venue_el] == h:
        return "venue_controls_horse"
    if kn.controlling[h] == venue_el:
        return "horse_controls_venue"
    return "no_relation"


# ---------------------------------------------------------------- 天運

def ten_score(kn: _Knowledge, rules: dict, horse_pillar: str, day_pillar_str: str) -> int:
    """干スコア+支スコア(2〜6)。点数はheat_v1.json、関係の定義は正本から。"""
    sc = rules["ten_scoring"]
    s1, b1 = horse_pillar[0], horse_pillar[1]
    s2, b2 = day_pillar_str[0], day_pillar_str[1]
    ss = sc["stem_score"]
    if s1 == s2:
        stem = ss["same_stem"]
    elif frozenset((s1, s2)) in kn.stem_union:
        stem = ss["stem_union"]
    else:
        e1, e2 = kn.stem_element[s1], kn.stem_element[s2]
        if kn.generating[e1] == e2 or kn.generating[e2] == e1:
            stem = ss["generating_either_direction"]
        elif e1 == e2:
            stem = ss["same_element_different_stem"]
        else:
            stem = ss["controlling_either_direction"]
    bs = sc["branch_score"]
    if b1 == b2:
        branch = bs["same_branch"]
    elif frozenset((b1, b2)) in kn.branch_union:
        branch = bs["branch_union"]
    elif frozenset((b1, b2)) in kn.branch_clash:
        branch = bs["branch_clash"]
    elif any(b1 in t and b2 in t for t in kn.trinities):
        branch = bs["branch_trinity_half"]
    else:
        branch = bs["otherwise"]
    return stem + branch


# ---------------------------------------------------------------- エンジン

class HeatEngine:
    """熱量v1。oshiスコアに地運・天運を重ねる。ギャップ点は存在しない。"""

    def __init__(self, rules: dict, sizhu: dict, geography: dict):
        self.rules = rules
        self.kn = _Knowledge(sizhu, geography)
        self.geography = geography
        verify_anchors(sizhu)

    def evaluate(self, *, oshi_score: float, horse_birth_date: str, target_date: str,
                 course_key: str, confidence: str = "full",
                 fit_rank: int | None = None, pop_rank: int | None = None) -> dict:
        day_p = day_pillar(target_date)
        horse_p = day_pillar(horse_birth_date)
        ven_el = venue_element(self.geography, course_key)
        rel = chi_relation(self.kn, horse_p[0], ven_el)
        chi = self.rules["chi_adjustments"]["values"][rel]
        ten = ten_score(self.kn, self.rules, horse_p, day_p)
        neutral = self.rules["ten_scoring"]["neutral"]
        w = self.rules["ten_scoring"]["weight_per_point"]
        heat = oshi_score + chi["adj"] + (ten - neutral) * w

        eligible = not (self.rules["eligibility"]["exclude_conf_low"] and confidence == "low")

        chips = []
        hh = self.rules["story_chips"]["hidden_heat"]
        if (fit_rank is not None and pop_rank is not None
                and fit_rank <= 3 and pop_rank - fit_rank >= 3):
            chips.append({"id": "hidden_heat", "label_ja": hh["label_ja"], "line": hh["line_ja"]})

        return {
            "heat": round(heat, 2),
            "eligible": eligible,
            "components": {
                "oshi": oshi_score,
                "chi": {"relation": rel, "label_ja": chi["label_ja"], "adj": chi["adj"],
                        "venue_element": ven_el},
                "ten": {"score": ten, "adj": (ten - neutral) * w},
            },
            "pillar": horse_p,
            "day_pillar": day_p,
            "story_chips": chips,
            "version": self.rules["meta"]["version"],
            "rule": "heat_v1(app_hypothesis)",
            "hypothesis_status": self.rules["meta"]["status"],
            "validation_status": self.rules["meta"]["validation"],
        }

    def race_stars(self, max_heat: float) -> int:
        for row in self.rules["race_stars"]["thresholds"]:
            if max_heat >= row["min"]:
                return row["stars"]
        return 1
