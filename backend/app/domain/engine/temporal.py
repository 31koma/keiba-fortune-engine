"""年運・月運・日運の知識部品。テーマ・層規則・適用可否は正本(temporal_cycles.json)。
day_themeの正はnumerology_core.meanings(temporal側はミラー、ロード時に一致検証済み)。
"""
from app.core.errors import KnowledgeGapError
from app.knowledge.loader import KnowledgeStore


def themes_for(kb: KnowledgeStore, number: int) -> dict:
    key = str(number)
    cyc = kb.temporal["cycle_themes"].get(key)
    canon = kb.numerology["meanings"].get(key, {})
    if cyc is None or not isinstance(cyc, dict):
        raise KnowledgeGapError(f"temporal_cycles.cycle_themes に {key} が未定義")
    return {
        "year_theme": cyc["year_theme"],
        "month_theme": cyc["month_theme"],
        "day_theme": canon.get("day_theme", cyc.get("day_theme")),  # 正=numerology_core
        "status": cyc.get("status"),
        "source_ids": cyc.get("source_ids", []),
    }


def applicability(kb: KnowledgeStore, cycle: str, entity_type: str) -> bool:
    matrix = kb.temporal["applicability_matrix"].get(cycle)
    if matrix is None:
        raise KnowledgeGapError(f"applicability_matrix に {cycle} が未定義")
    if str(matrix.get("status", "")).startswith("on_hold"):
        return False
    return bool(matrix.get(entity_type, False))


def layered_parts(kb: KnowledgeStore, py: int, pm: int, pd: int) -> dict:
    """正本 combination_rules.layering: 平均・合算せず層として並べる(日=前景, 月=中景, 年=背景)。
    resonance: 年月日同数なら強調1文に統合(重複列挙しない)。"""
    rules = kb.temporal["combination_rules"]
    roles = kb.temporal["period_roles"]
    out = {
        "foreground_day": {"number": pd, **themes_for(kb, pd),
                           "role_ja": roles["personal_day"]["role_ja"]},
        "middle_month": {"number": pm, **themes_for(kb, pm),
                         "role_ja": roles["personal_month"]["role_ja"]},
        "background_year": {"number": py, **themes_for(kb, py),
                            "role_ja": roles["personal_year"]["role_ja"]},
        "layering_rule": rules["layering"]["rule"],
        "rule_status": rules["layering"]["status"],
    }
    if py == pm == pd:
        # 正本 resonance 規則の文言をそのまま使用
        out["resonance"] = {
            "note": rules["resonance"]["rule"],
            "status": rules["resonance"]["status"],
        }
    return out
