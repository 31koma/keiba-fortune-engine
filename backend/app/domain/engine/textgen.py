"""鑑定文組み立て。テンプレート・語り口・スコア帯は正本(horse/human_expression_templates.json)。
プレースホルダ不足は補完せずKnowledgeGapErrorとする(正本側への追加提案対象)。
"""
import re

from app.core.errors import KnowledgeGapError
from app.knowledge.loader import KnowledgeStore

_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")


def fill(template: str, ctx: dict) -> str:
    def repl(m: re.Match) -> str:
        token = m.group(1)
        cur = ctx
        for part in token.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                raise KnowledgeGapError(
                    f"テンプレートのプレースホルダ {{{token}}} に対応する値がありません")
        return str(cur)
    return _TOKEN.sub(repl, template)


def parse_score_bands(bands: dict) -> list[tuple[str, str, float | None, float | None, str]]:
    """正本のスコア帯キー(例 'high(>=2.5)' 'mid(1.5-2.5)' 'low(<1.5)')を解析。"""
    out = []
    for key, text in bands.items():
        m = re.match(r"(\w+)\(>=([\d.]+)\)", key)
        if m:
            out.append((m.group(1), key, float(m.group(2)), None, text))
            continue
        m = re.match(r"(\w+)\(([\d.]+)-([\d.]+)\)", key)
        if m:
            out.append((m.group(1), key, float(m.group(2)), float(m.group(3)), text))
            continue
        m = re.match(r"(\w+)\(<([\d.]+)\)", key)
        if m:
            out.append((m.group(1), key, None, float(m.group(2)), text))
            continue
        raise KnowledgeGapError(f"score_bandsのキー形式を解釈できません: {key}")
    return out


def band_for(bands: dict, score: float) -> dict:
    for name, key, lo, hi, text in parse_score_bands(bands):
        if lo is not None and hi is None and score >= lo:
            return {"band": name, "key": key, "text": text}
        if lo is not None and hi is not None and lo <= score < hi:
            return {"band": name, "key": key, "text": text}
        if lo is None and hi is not None and score < hi:
            return {"band": name, "key": key, "text": text}
    raise KnowledgeGapError(f"score={score} がどのスコア帯にも該当しません")


def render(kb: KnowledgeStore, template_key: str, ctx: dict,
           target: str = "horse") -> dict:
    src = kb.horse_templates if target == "horse" else kb.human_templates
    tpl = src["templates"].get(template_key)
    if tpl is None:
        raise KnowledgeGapError(f"{target}_expression_templates に {template_key} が未定義")
    return {"text": fill(tpl["text_ja"], ctx), "template": template_key,
            "status": tpl.get("status")}
