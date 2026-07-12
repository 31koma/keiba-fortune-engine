"""CI/テスト用 Mock知識ベース生成器。

正本(Google Drive)の代替ではない。構造(キー・型・相互参照)は正本と同一だが、
解釈テキストは全て「試験〜」のテスト用文言。占術知識としての意味を持たない。
リポジトリには生成器(本ファイル)のみを置き、知識データは実行時に生成する。
"""
import hashlib
import json
import sys
from pathlib import Path

NUMS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "22", "33"]

SIGNS = [
    (1, "牡羊座", "Aries", "03-21", "04-19", "fire", "cardinal"),
    (2, "牡牛座", "Taurus", "04-20", "05-20", "earth", "fixed"),
    (3, "双子座", "Gemini", "05-21", "06-21", "air", "mutable"),
    (4, "蟹座", "Cancer", "06-22", "07-22", "water", "cardinal"),
    (5, "獅子座", "Leo", "07-23", "08-22", "fire", "fixed"),
    (6, "乙女座", "Virgo", "08-23", "09-22", "earth", "mutable"),
    (7, "天秤座", "Libra", "09-23", "10-23", "air", "cardinal"),
    (8, "蠍座", "Scorpio", "10-24", "11-22", "water", "fixed"),
    (9, "射手座", "Sagittarius", "11-23", "12-21", "fire", "mutable"),
    (10, "山羊座", "Capricorn", "12-22", "01-19", "earth", "cardinal"),
    (11, "水瓶座", "Aquarius", "01-20", "02-18", "air", "fixed"),
    (12, "魚座", "Pisces", "02-19", "03-20", "water", "mutable"),
]

PYTHAGOREAN = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}

SRC = ["test_source"]
HEAD = {"schema_version": "0.0-fixture", "domain": "", "updated": "0000-00-00"}


def _head(domain):
    d = dict(HEAD)
    d["domain"] = domain
    return d


def _parts(prefix, seed):
    lv = lambda k: ((seed * 7 + k) % 5) + 1  # noqa: E731 1..5に分散
    return {
        "essence": f"試験本質{prefix}", "strengths": f"試験強み{prefix}",
        "weaknesses": f"試験弱み{prefix}", "behavior": f"試験行動{prefix}",
        "focus": f"試験集中{prefix}",
        "caution": {"level": lv(1), "text": f"試験慎重{prefix}"},
        "drive": {"level": lv(2), "text": f"試験積極{prefix}"},
        "stability": {"level": lv(3), "text": f"試験安定{prefix}"},
        "adaptability": {"level": lv(4), "text": f"試験適応{prefix}"},
        "day_tailwind": f"試験追い風{prefix}", "day_caution": f"試験注意{prefix}",
        "compat_complement": f"試験補完{prefix}", "compat_clash": f"試験衝突{prefix}",
    }


def build_mock_kb(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    files = {}

    files["numerology_core.json"] = {
        **_head("numerology_core"),
        "default_policy": {"system": "pythagorean", "reduction_method": "decoz_component",
                           "master_numbers": [11, 22, 33],
                           "name_romanization": "hepburn_no_macron",
                           "disclaimer_required": True},
        "systems": {"pythagorean": {"label_ja": "試験式", "status": "adopted",
                                    "letter_values": PYTHAGOREAN,
                                    "vowels": ["A", "E", "I", "O", "U"],
                                    "y_rule": "試験: 子音扱い", "source_ids": SRC}},
        "reduction": {"decoz_component": {"label_ja": "試験還元", "status": "adopted",
                                          "algorithm": "試験", "source_ids": SRC},
                      "master_number_stop": "11/22/33で停止"},
        "calculations": {k: {"label_ja": f"試験{k}", "formula": "試験",
                             "applies_to": ["person", "horse", "jockey"],
                             "horse_status": "direct" if k in
                             ("life_path", "birthday_number", "personal_year",
                              "personal_month", "personal_day") else "app_hypothesis",
                             "source_ids": SRC}
                         for k in ("life_path", "birthday_number", "expression",
                                   "soul_urge", "personality", "personal_year",
                                   "personal_month", "personal_day",
                                   "universal_year", "universal_day")},
        "meanings": {**{n: {"keywords_ja": [f"試験{n}"], "positive": f"試験正{n}",
                            "negative": f"試験負{n}", "day_theme": f"試験日テーマ{n}",
                            "race_theme_hypothesis": f"試験仮説{n}"} for n in NUMS},
                     "_meta": {"race_theme_hypothesis_status": "app_hypothesis",
                               "note": "fixture", "source_ids": SRC}},
        "compatibility": {"group_method": {
            "status": "adopted_as_convention",
            "groups": {"independent": {"numbers": [1, 5, 7], "label_ja": "試験A"},
                       "practical": {"numbers": [2, 4, 8], "label_ja": "試験B"},
                       "harmonious": {"numbers": [3, 6, 9], "label_ja": "試験C"}},
            "rules": [{"if": "same_group", "score": 3, "label_ja": "試験同組"},
                      {"if": "same_number", "score": 3, "label_ja": "試験同数"},
                      {"if": "different_group", "score": 2, "label_ja": "試験異組"}],
            "note": "fixture", "source_ids": SRC}},
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    files["zodiac_core.json"] = {
        **_head("zodiac_core"),
        "default_policy": {"zodiac_type": "tropical", "sign_basis": "sun_sign_only",
                           "birth_time": "not_required_design",
                           "boundary_handling": "試験: 境界日(±1日)はboundary_flag",
                           "disclaimer_required": True},
        "signs": [{"id": i, "name_ja": ja, "name_en": en, "start_md": s, "end_md": e,
                   "element": el, "modality": mo, "keywords_ja": [f"試験{ja}"],
                   "race_theme_hypothesis": f"試験{ja}"}
                  for i, ja, en, s, e, el, mo in SIGNS],
        "signs_meta": {"note": "fixture"},
        "elements": {"fire": {"label_ja": "火", "keywords_ja": ["試験"],
                              "harmonious_with": ["fire", "air"],
                              "tense_with": ["water", "earth"]},
                     "earth": {"label_ja": "地", "keywords_ja": ["試験"],
                               "harmonious_with": ["earth", "water"],
                               "tense_with": ["fire", "air"]},
                     "air": {"label_ja": "風", "keywords_ja": ["試験"],
                             "harmonious_with": ["air", "fire"],
                             "tense_with": ["earth", "water"]},
                     "water": {"label_ja": "水", "keywords_ja": ["試験"],
                               "harmonious_with": ["water", "earth"],
                               "tense_with": ["fire", "air"]}},
        "compatibility": {
            "distance_method": {"status": "adopted_as_convention",
                                "algorithm": "distance = min(|a-b|, 12-|a-b|)",
                                "distance_table": {
                                    "0": {"aspect": "conjunction", "degrees": 0, "score": 3, "label_ja": "試験0"},
                                    "1": {"aspect": "semi_sextile", "degrees": 30, "score": 1, "label_ja": "試験1"},
                                    "2": {"aspect": "sextile", "degrees": 60, "score": 3, "label_ja": "試験2"},
                                    "3": {"aspect": "square", "degrees": 90, "score": 1, "label_ja": "試験3"},
                                    "4": {"aspect": "trine", "degrees": 120, "score": 3, "label_ja": "試験4"},
                                    "5": {"aspect": "quincunx", "degrees": 150, "score": 1, "label_ja": "試験5"},
                                    "6": {"aspect": "opposition", "degrees": 180, "score": 2, "label_ja": "試験6"}},
                                "source_ids": SRC},
            "element_method": {"status": "adopted_as_convention",
                               "algorithm": "同元素=3, harmonious=3, tense=1",
                               "source_ids": SRC},
            "combined_score": {"status": "app_hypothesis",
                               "algorithm": "distance_method(0.6) + element_method(0.4)",
                               "note": "fixture"}},
        "planets": {"note": "fixture"},
        "timing": {"note": "fixture"},
        "birth_time_requirements": {"note": "fixture"},
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    inum = {n: _parts(f"数{n}", int(n)) for n in ("1", "2", "3", "4", "5", "6", "7", "8", "9")}
    inum["11"] = {"inherits": "2", "overrides": {"essence": "試験M11"},
                  "status": "established_interpretation"}
    inum["22"] = {"inherits": "4", "overrides": {"essence": "試験M22"},
                  "status": "established_interpretation"}
    inum["33"] = {"inherits": "6", "overrides": {"essence": "試験M33"},
                  "status": "school_specific(試験)"}
    files["interpretation_templates.json"] = {
        **_head("interpretation_templates"),
        "design_principle": "fixture", "status_vocab": "status_vocab.json",
        "part_keys": {k: {"label_ja": f"試験{k}"} for k in
                      ("essence", "strengths", "weaknesses", "behavior", "focus",
                       "caution", "drive", "stability", "adaptability",
                       "day_tailwind", "day_caution",
                       "compat_complement", "compat_clash")},
        "part_status": {"essence,strengths,weaknesses,behavior,focus":
                        "established_interpretation",
                        "levels_calibration": "validation_required"},
        "numbers": inum,
        "signs": {str(i): _parts(ja, i + 20) for i, ja, *_ in SIGNS},
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    groups = ["independent", "practical", "harmonious"]
    elements = ["fire", "earth", "air", "water"]
    files["number_zodiac_combinations.json"] = {
        **_head("number_zodiac_combinations"),
        "design_principle": "fixture", "status": "app_hypothesis",
        "verification": "fixture",
        "combination_algorithm": {
            "step0_part_selection": {"rule": "fixture", "map": {}, "status": "app_hypothesis"},
            "step1_axes": {"rule": "fixture", "formula": "round((a+b)/2)",
                           "axis_phrases": {ax: {str(l): f"試験{ax}文{l}" for l in range(1, 6)}
                                            for ax in ("drive", "caution", "stability", "adaptability")}},
            "step2_synergy": {"rule": "fixture",
                              "matrix": {f"{g}_{e}": {"tone_ja": f"試験基調{g}_{e}",
                                                      "emphasis": ["drive"],
                                                      "watch": f"試験監視{g}_{e}"}
                                         for g in groups for e in elements}},
            "step3_contradiction": {"rule": "drive差3以上でギャップ文",
                                    "gap_template_ja": "試験ギャップ({number.drive.text}/{sign.drive.text})"},
            "step4_master_numbers": {"rule": "inherits+overrides", "note": "33はOFF可"},
            "step5_dedupe": {"rule": "fixture"}},
        "priority_when_conflict": ["step3_contradiction", "step2_synergy", "step1_axes"],
        "output_contract": {"note": "fixture", "produces": ["axes", "tone", "watch"]},
        "example": {"note": "fixture"},
        "sources": {"canonical": "sources_master.json", "source_ids_used": ["app_original"]},
    }

    files["horse_expression_templates.json"] = {
        **_head("horse_expression_templates"), "priority": "fixture",
        "language_policy": {
            "rule_ja": "試験: 断定しない",
            "required_suffix_patterns": ["〜が出やすい流れ"],
            "forbidden_expressions": {"status": "rejected",
                                      "list": ["必ず勝つ", "絶対", "確実に", "的中保証", "回収率"],
                                      "note": "fixture"},
            "required_disclaimer_ja": "本鑑定は占術に基づくエンターテインメントであり、レース結果を予測・保証するものではありません。",
            "status": "app_hypothesis"},
        "placeholders": {"{horse_name}": "試験"},
        "templates": {
            "horse_profile": {"text_ja": "試験P:{horse_name} 数{num}({p.essence})×{sign}({p.sign_essence}) 基調{tone} {p.behavior} {axes.stability} 強み{p.strengths} 注意{watch}",
                              "status": "app_hypothesis"},
            "horse_race_day": {"text_ja": "試験D:{race_date} 数{pd}({pd_theme}) 追い風{p.day_tailwind} {axes.drive} 注意{p.day_caution}",
                               "status": "app_hypothesis"},
            "horse_jockey": {"text_ja": "試験J:馬({horse_sign}・{horse_num})×騎手({jockey_sign}・{jockey_num}) {aspect_label}/{group_label} 補完{p.compat_complement} 衝突{p.compat_clash}",
                             "variant_low_score_ja": "試験J低:{aspect_label}/{group_label}",
                             "status": "app_hypothesis"},
            "horse_triad": {"text_ja": "試験T:{score_band} {pd_theme} {aspect_label} {tone} {axes.drive} {watch}",
                            "score_bands": {"high(>=2.5)": "試験帯高",
                                            "mid(1.5-2.5)": "試験帯中",
                                            "low(<1.5)": "試験帯低"},
                            "status": "app_hypothesis"},
            "horse_year_month": {"text_ja": "試験Y:{year}年PY{py}({py_theme}) {month}月({pm_theme}) {p.day_tailwind}",
                                 "status": "app_hypothesis"}},
        "distribution_caveat": "fixture",
        "sources": {"canonical": "sources_master.json", "source_ids_used": ["app_original"]},
    }

    files["human_expression_templates.json"] = {
        **_head("human_expression_templates"), "priority": "fixture",
        "language_policy": {"note": "fixture"},
        "templates": {"human_profile": {"text_ja": "試験H:{p.essence}",
                                        "status": "app_hypothesis"}},
        "shared_data_note": "fixture", "placeholders_note": "fixture",
        "sources": {"canonical": "sources_master.json", "source_ids_used": ["app_original"]},
    }

    files["temporal_cycles.json"] = {
        **_head("temporal_cycles"), "design_principle": "fixture",
        "integration": {"note": "fixture"},
        "period_roles": {k: {"role_ja": f"試験{k}", "use_for": ["試験"],
                             "narrative_layer": "試験"}
                         for k in ("personal_year", "personal_month",
                                   "personal_day", "universal_day")},
        "cycle_themes": {n: {"year_theme": f"試験年{n}", "month_theme": f"試験月{n}",
                             "day_theme": f"試験日テーマ{n}",
                             "status": "established_interpretation",
                             "source_ids": SRC} for n in NUMS},
        "combination_rules": {
            "layering": {"rule": "試験: 層として並べる", "status": "app_hypothesis"},
            "resonance": {"rule": "試験: 同数は強調1文に統合", "status": "app_hypothesis"},
            "contradiction": {"rule": "試験: 日>月>年", "status": "app_hypothesis"},
            "master_in_cycles": {"rule": "試験: 既定保持", "status": "school_specific"}},
        "target_expression_rules": {"note": "fixture"},
        "template_additions_to_merge": {},
        "applicability_matrix": {
            "personal_year": {"horse": True, "jockey": True, "race_day": False,
                              "human": True, "requires": "birth_date"},
            "personal_month": {"horse": True, "jockey": True, "race_day": False,
                               "human": True, "requires": "birth_date"},
            "personal_day": {"horse": True, "jockey": True, "race_day": False,
                             "human": True, "requires": "birth_date + target_date"},
            "universal_day": {"horse": False, "jockey": False, "race_day": True,
                              "human": False, "requires": "target_date only"},
            "jupiter_saturn_year": {"horse": True, "jockey": True, "race_day": False,
                                    "human": True, "requires": "ephemeris",
                                    "status": "on_hold(試験)"},
            "moon_day": {"horse": False, "jockey": False, "race_day": True,
                         "human": True, "requires": "ephemeris",
                         "status": "on_hold(試験)"}},
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    files["sources_master.json"] = {
        **_head("sources_master"), "note": "fixture",
        "aliases": {},
        "sources": {"test_source": {"title": "テスト用出典", "author": "fixture",
                                    "year": "-", "url": "", "reliability": "high"},
                    "app_original": {"title": "テスト用アプリ定義", "author": "fixture",
                                     "year": "-", "url": "",
                                     "reliability": "n/a(app_hypothesis)"}},
    }

    files["status_vocab.json"] = {
        **_head("status_vocab"),
        "families": {"interpretation_status": ["established_interpretation",
                                               "school_specific", "app_hypothesis",
                                               "validation_required", "rejected"],
                     "adoption_status": ["adopted", "on_hold", "rejected",
                                         "adopted_as_reference",
                                         "adopted_as_convention",
                                         "rejected_for_scraping"],
                     "verification_status": ["pre_registered", "validated_association",
                                             "not_supported_by_data",
                                             "data_insufficient"],
                     "factual_status": ["established_fact"]},
        "aliases": {},
        "rule": "括弧付き注記は許可。先頭語が語彙に一致すること",
    }

    files["ephemeris_policy.json"] = {
        **_head("ephemeris_policy"), "purpose": "fixture",
        "integration": {"note": "fixture"},
        "required_bodies": {"sun": {"use": "試験", "priority": "must"}},
        "time_precision_requirements": {"note": "fixture"},
        "unknown_birth_time_policy": {"status": "adopted", "rule": "試験正午法"},
        "unknown_birth_place_policy": {"status": "adopted", "rule": "試験"},
        "timezone_and_dst": {"status": "adopted", "rule": "試験"},
        "julian_day_and_frames": {"note": "fixture"},
        "cusp_determination_spec": {"status": "adopted", "method": "試験"},
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    files["horse_data_policy.json"] = {
        **_head("horse_data_policy"), "purpose": "fixture",
        "name_normalization": {"principle": "試験"},
        "data_sources": {"note": "fixture"},
        "input_minimum": {"horse": ["birth_date"], "jockey": ["birth_date"],
                          "race": ["race_date"]},
        "legal_checklist": ["試験"],
        "sources": {"canonical": "sources_master.json", "source_ids_used": SRC},
    }

    files["verification_plan.json"] = {
        **_head("verification_plan"), "type": "fixture", "principle": "試験",
        "lock_rule": "試験", "amendments": [],
        "hypotheses": [{"id": "H1", "status": "pre_registered"}],
        "outcomes": [], "confounders_and_controls": ["試験"],
        "exclusions_pre_registered": [], "data_window": "試験",
    }

    schema_sql = ("-- fixture schema(テスト用。正本schema.sqlではない)\n"
                  "CREATE TABLE sources (source_id TEXT PRIMARY KEY);\n")

    rows = []
    for name, data in files.items():
        raw = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
        (out / name).write_bytes(raw)
        rows.append((name, len(raw), hashlib.sha256(raw).hexdigest()[:16]))
    raw = schema_sql.encode("utf-8")
    (out / "schema.sql").write_bytes(raw)
    rows.append(("schema.sql", len(raw), hashlib.sha256(raw).hexdigest()[:16]))

    manifest = out / "kb_manifest.md"
    lines = ["# Mock知識ベース(テスト用フィクスチャ。正本ではない)", "",
             "- 生成: backend/tests/mock_kb.py",
             "- 版: 00_正本_知識ベース_v0.0_00000000 (fixture)", "",
             "| ファイル | bytes | SHA-256先頭16桁 |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {h} |" for n, s, h in sorted(rows)]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./mock_kb_out")
    m = build_mock_kb(target)
    print(f"mock kb generated: {target} (manifest: {m})")
