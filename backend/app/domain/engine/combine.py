"""数字×星座の意味合成。規則は正本 number_zodiac_combinations.json の
combination_algorithm(step0〜step5)をそのまま実行する。文言・行列・レベル文は全て正本。
"""
import math

from app.core.errors import KnowledgeGapError
from app.knowledge.loader import KnowledgeStore

_AXES = ["drive", "caution", "stability", "adaptability"]


def _digit_base(n: int) -> int:
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def resolve_number_entry(kb: KnowledgeStore, number: int, master33: bool = True) -> dict:
    numbers = kb.interpretation["numbers"]
    key = str(number)
    if number == 33 and not master33:
        key = "6"  # 正本注記「33を認めない流派あり。設定でOFF可」→ベース数を使用
    entry = numbers.get(key)
    if entry is None:
        raise KnowledgeGapError(f"interpretation_templates.numbers に {key} が未定義")
    if "inherits" in entry:  # step4: マスターはベース数+overrides
        base = dict(numbers[entry["inherits"]])
        base.update(entry.get("overrides", {}))
        base["_master_of"] = entry["inherits"]
        return base
    return dict(entry)


def compose(kb: KnowledgeStore, number: int, sign_id: int,
            master33: bool = True) -> dict:
    """出力契約(output_contract): axes / tone / emphasis_parts / watch / gap_sentence"""
    alg = kb.combinations["combination_algorithm"]
    num_e = resolve_number_entry(kb, number, master33)
    sign_e = kb.interpretation["signs"].get(str(sign_id))
    if sign_e is None:
        raise KnowledgeGapError(f"interpretation_templates.signs に {sign_id} が未定義")

    # step1: 4軸 = 数字と星座のlevel平均を五段階に丸め、正本のレベル文を付す
    axes = {}
    phrases = alg["step1_axes"]["axis_phrases"]
    for ax in _AXES:
        level = math.floor((num_e[ax]["level"] + sign_e[ax]["level"]) / 2 + 0.5)
        text = phrases[ax].get(str(level))
        if text is None:
            raise KnowledgeGapError(f"axis_phrases.{ax} にレベル{level}が未定義")
        axes[ax] = {"level": level, "text": text}

    # step2: 数字グループ×星座元素の基調トーン(正本matrix)
    groups = kb.numerology["compatibility"]["group_method"]["groups"]
    base_num = _digit_base(number)
    group = next((g for g, v in groups.items() if base_num in v["numbers"]), None)
    zsign = next(s for s in kb.zodiac["signs"] if s["id"] == sign_id)
    synergy_key = f"{group}_{zsign['element']}"
    cell = alg["step2_synergy"]["matrix"].get(synergy_key)
    if cell is None:
        raise KnowledgeGapError(f"step2_synergy.matrix に {synergy_key} が未定義")

    # step3: driveレベル差3以上で内外ギャップ文(正本テンプレート)
    gap_sentence = None
    if abs(num_e["drive"]["level"] - sign_e["drive"]["level"]) >= 3:
        gap_sentence = (alg["step3_contradiction"]["gap_template_ja"]
                        .replace("{number.drive.text}", num_e["drive"]["text"])
                        .replace("{sign.drive.text}", sign_e["drive"]["text"]))

    # step5: 数字と星座の同文重複は強調表現に統合
    def dedupe(a: str, b: str) -> str:
        if a == b:
            return f"{a}(その傾向が特に強い)"  # 正本step5の規則に基づく統合
        return f"{a}。{b}" if a != b else a

    # step0: 部品選択(正本map: 数字優先/星座優先/併記)
    parts = {
        "essence": num_e["essence"],                 # 併記(テンプレート側にsign_essence枠)
        "sign_essence": sign_e["essence"],
        "behavior": (dedupe(num_e["behavior"], sign_e["behavior"])
                     if gap_sentence else sign_e["behavior"]),   # 星座優先/ギャップ時両記
        "strengths": num_e["strengths"],             # 数字優先
        "weaknesses": sign_e["weaknesses"],          # 星座優先
        "focus": sign_e["focus"],                    # 星座優先
        "day_tailwind_sign": sign_e["day_tailwind"],  # 展開・馬場文脈=星座
        "day_caution_sign": sign_e["day_caution"],
        "compat_complement": f"{sign_e['compat_complement']}、{num_e['compat_complement']}",
        "compat_clash": f"{sign_e['compat_clash']}、{num_e['compat_clash']}",
    }

    return {
        "axes": axes,
        "tone": cell["tone_ja"],
        "emphasis_parts": cell["emphasis"],
        "watch": cell["watch"],
        "gap_sentence": gap_sentence,
        "synergy_key": synergy_key,
        "parts": parts,
        "number_entry": num_e,
        "sign_entry": sign_e,
        "status": kb.combinations["status"],
        "rule": "number_zodiac_combinations.combination_algorithm",
        "source_ids": kb.combinations.get("sources", {}).get("source_ids_used", []),
    }
