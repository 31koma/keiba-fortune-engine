"""鑑定ユースケース。DTO→占術エンジン→合成→鑑定文→禁止語フィルタの流れを組み立てる。
知識・重み・文言は一切持たない(全て正本参照)。
"""
from datetime import date

from app.core.errors import KnowledgeGapError
from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO
from app.domain.engine import combine, temporal, textgen
from app.domain.engine.numerology import Numerology
from app.domain.engine.wordfilter import ForbiddenFilter
from app.domain.engine.zodiac import Zodiac
from app.knowledge.loader import KnowledgeStore


class ReadingService:
    def __init__(self, kb: KnowledgeStore, num: Numerology, zod: Zodiac,
                 ffilter: ForbiddenFilter, master33: bool = True):
        self.kb = kb
        self.num = num
        self.zod = zod
        self.filter = ffilter
        self.master33 = master33

    # ---------- profile ----------
    def profile(self, entity_type: str, birth_date: date,
                name_roman: str | None = None) -> dict:
        used_rules: list[str] = []
        source_ids: set[str] = set()

        def track(r: dict) -> dict:
            used_rules.append(r["rule"])
            source_ids.update(r.get("source_ids", []))
            return r

        core = {
            "life_path": track(self.num.life_path(birth_date)),
            "birthday_number": track(self.num.birthday_number(birth_date)),
        }
        # 名前系: 馬はapp_hypothesis(正本 horse_status)。名前が無ければ計算しない(補完しない)
        if name_roman:
            core["expression"] = track(self.num.expression(name_roman))
            core["soul_urge"] = track(self.num.soul_urge(name_roman))
            core["personality"] = track(self.num.personality(name_roman))

        sun = self.zod.sign_for_date(birth_date)
        used_rules.append(sun["rule"])
        source_ids.update(sun.get("source_ids", []))

        statuses = {k: v.get("horse_status") for k, v in core.items()} \
            if entity_type == "horse" else {k: "direct" for k in core}
        return {
            "entity_type": entity_type,
            "birth_date": birth_date.isoformat(),
            "core_numerology": {k: {kk: vv for kk, vv in v.items() if kk != "rule"}
                                for k, v in core.items()},
            "sun_sign": sun,
            "calculated_attributes": {
                "numerology_system": self.num.system_id,
                "master_numbers": self.num.masters,
            },
            "used_rules": used_rules,
            "source_ids": sorted(source_ids),
            "status": statuses,
        }

    # ---------- day fortune ----------
    def day_fortune(self, entity_type: str, birth_date: date, target: date) -> dict:
        used_rules: list[str] = []

        def track(r: dict) -> int:
            used_rules.append(r["rule"])
            return r["value"]

        py = track(self.num.personal_year(birth_date, target.year))
        pm = track(self.num.personal_month(py, target.month))
        pd = track(self.num.personal_day(pm, target.day))
        ud = track(self.num.universal_day(target))

        def meanings(n: int) -> dict:
            # 正本numerology_core.meanings(keywords/positive/negative)を添える。
            # 完成文は生成しない(temporal_cycles.design_principle準拠)
            m = self.kb.numerology["meanings"].get(str(n), {})
            return {"keywords_ja": m.get("keywords_ja", []),
                    "positive": m.get("positive"), "negative": m.get("negative")}

        parts = temporal.layered_parts(self.kb, py, pm, pd)
        result = {
            "entity_type": entity_type,
            "target_date": target.isoformat(),
            "personal_year": {"value": py, **temporal.themes_for(self.kb, py),
                              "meanings": meanings(py)},
            "personal_month": {"value": pm, **temporal.themes_for(self.kb, pm),
                               "meanings": meanings(pm)},
            "personal_day": {"value": pd, **temporal.themes_for(self.kb, pd),
                             "meanings": meanings(pd)},
            "universal_day": {"value": ud,
                              "applies_to": "race_day",  # 正本applicability_matrix
                              **temporal.themes_for(self.kb, ud)},
            "interpretation_parts": parts,
            "used_rules": used_rules,
        }
        return result

    # ---------- month calendar ----------
    def month_calendar(self, entity_type: str, birth_date: date,
                       year: int, month: int) -> dict:
        """月の日ごとのパーソナルデー数字+テーマ(日別カレンダー用)。
        正本period_roles.personal_day.use_forに「日別カレンダー」が定義済み。
        テーマ語の列挙のみで吉凶の断定はしない(誠実原則)。"""
        import calendar as _cal
        used_rules: list[str] = []

        def track(r: dict) -> int:
            if r["rule"] not in used_rules:
                used_rules.append(r["rule"])
            return r["value"]

        py = track(self.num.personal_year(birth_date, year))
        pm = track(self.num.personal_month(py, month))
        days = []
        for d in range(1, _cal.monthrange(year, month)[1] + 1):
            pd = track(self.num.personal_day(pm, d))
            t = temporal.themes_for(self.kb, pd)
            days.append({"date": date(year, month, d).isoformat(),
                         "weekday": date(year, month, d).weekday(),
                         "value": pd, "day_theme": t["day_theme"]})
        return {
            "entity_type": entity_type,
            "year": year, "month": month,
            "personal_year": {"value": py, **temporal.themes_for(self.kb, py)},
            "personal_month": {"value": pm, **temporal.themes_for(self.kb, pm)},
            "days": days,
            "used_rules": used_rules,
        }

    # ---------- triad ----------
    def horse_triad(self, horse: HorseDTO, jockey: JockeyDTO, race: RaceDTO,
                    target: date, provider_credit: dict) -> dict:
        kb = self.kb
        h_prof = self.profile("horse", horse.birth_date, horse.official_english_name)
        j_prof = self.profile("jockey", jockey.birth_date, jockey.name_roman)

        h_num = h_prof["core_numerology"]["life_path"]["value"]
        j_num = j_prof["core_numerology"]["life_path"]["value"]
        h_sign = h_prof["sun_sign"]
        j_sign = j_prof["sun_sign"]

        # 日運(馬×レース日)
        h_day = self.day_fortune("horse", horse.birth_date, target)
        pd = h_day["personal_day"]["value"]
        ud_info = self.num.universal_day(target)

        # 相性コンポーネント(正本定義の各手法。最終重みは未確定=確定しない)
        dist = self.zod.distance_compat(h_sign["sign_id"], j_sign["sign_id"])
        elem = self.zod.element_compat(h_sign["element"], j_sign["element"])
        group = self.num.group_compat(kb, h_num, j_num)
        zcombined = self.zod.combined_score(
            h_sign["sign_id"], j_sign["sign_id"], h_sign["element"], j_sign["element"])

        # 数字×星座の意味合成(馬)
        comp = combine.compose(kb, h_num, h_sign["sign_id"], self.master33)
        pd_entry = combine.resolve_number_entry(kb, pd, self.master33)
        pd_theme = temporal.themes_for(kb, pd)["day_theme"]

        axes_text = {k: v["text"] for k, v in comp["axes"].items()}
        parts_ctx = {
            **comp["parts"],
            # 日運文脈=数字(正本step0: パーソナルデイの数)
            "day_tailwind": pd_entry["day_tailwind"],
            "day_caution": pd_entry["day_caution"],
        }

        # --- 鑑定文(テンプレートは正本、生成後に禁止語フィルタ必須) ---
        texts: list[dict] = []
        ctx_race_day = {"race_date": race.race_date.isoformat(), "pd": pd,
                        "pd_theme": pd_theme, "p": parts_ctx, "axes": axes_text}
        texts.append(textgen.render(kb, "horse_race_day", ctx_race_day))

        ctx_jockey = {"horse_sign": h_sign["name_ja"], "horse_num": h_num,
                      "jockey_sign": j_sign["name_ja"], "jockey_num": j_num,
                      "aspect_label": dist["label_ja"], "group_label": group["label_ja"],
                      "p": parts_ctx}
        texts.append(textgen.render(kb, "horse_jockey", ctx_jockey))

        # スコア帯: 帯の閾値・文言は正本(horse_triad.score_bands)。
        # ただし帯へ入力する統合スコアの正式定義は正本に未確定のため、
        # 暫定でzodiac.combined_score(正本定義のapp_hypothesis)を使用し、
        # hypothesis扱い+validation_requiredを明示する。
        bands = kb.horse_templates["templates"]["horse_triad"]["score_bands"]
        band = textgen.band_for(bands, zcombined["score"])
        ctx_triad = {"score_band": band["text"], "pd_theme": pd_theme,
                     "aspect_label": dist["label_ja"], "tone": comp["tone"],
                     "axes": axes_text, "watch": comp["watch"]}
        texts.append(textgen.render(kb, "horse_triad", ctx_triad))

        generated = "\n\n".join(t["text"] for t in texts)
        if comp["gap_sentence"]:
            generated += "\n\n" + comp["gap_sentence"]
        generated = self.filter.apply(generated)  # 禁止語フィルタ(必須)

        used_rules = sorted(set(
            h_prof["used_rules"] + j_prof["used_rules"] + h_day["used_rules"]
            + [dist["rule"], elem["rule"], group["rule"], zcombined["rule"], comp["rule"]]))
        source_ids = sorted(set(
            h_prof["source_ids"] + j_prof["source_ids"]
            + dist["source_ids"] + elem["source_ids"] + group["source_ids"]
            + comp["source_ids"]))

        return {
            "horse_profile": h_prof,
            "jockey_profile": j_prof,
            "race_day_profile": {
                "race_date": race.race_date.isoformat(),
                "universal_day": {"value": ud_info["value"],
                                  "day_theme": temporal.themes_for(kb, ud_info["value"])["day_theme"]},
                "horse_personal_day": h_day["personal_day"],
            },
            "compatibility_components": {
                "zodiac_distance": dist,
                "zodiac_element": elem,
                "numerology_group": group,
                "zodiac_combined_score": zcombined,
            },
            "unweighted_raw_features": {
                "horse_life_path": h_num, "jockey_life_path": j_num,
                "horse_sign_id": h_sign["sign_id"], "jockey_sign_id": j_sign["sign_id"],
                "horse_personal_day": pd, "universal_day": ud_info["value"],
                "distance_score": dist["score"], "element_score": elem["score"],
                "group_score": group["score"],
                "note": "triadの最終重み・配点は正本で未確定のため統合していない",
            },
            "score_band_provisional": {
                **band,
                "score_basis": "zodiac.combined_score(app_hypothesis)を暫定使用。"
                               "triad統合スコアの正式定義は正本側で未確定",
            },
            "generated_interpretation": generated,
            "disclaimer": self.filter.disclaimer,
            "provider_credit": provider_credit,
            "used_rules": used_rules,
            "source_ids": source_ids,
            "hypothesis_status": "app_hypothesis",
            "validation_status": "validation_required",
        }
