"""数秘術の決定的計算。文字値・マスターナンバー・式の定義は正本(numerology_core.json)から取得。

計算式は正本 calculations[*].formula の記述を実装したもの:
- life_path: reduce(month)+reduce(day)+reduce(year) を再還元(Decoz法)
- personal_year: reduce(birth_month)+reduce(birth_day)+reduce(target_year) を再還元
- personal_month: reduce(personal_year + target_month)
- personal_day: reduce(personal_month + reduce(target_day))
- universal_day: reduce(y+m+d全桁)
"""
from datetime import date

from app.core.errors import KnowledgeGapError
from app.knowledge.loader import KnowledgeStore


def _digit_sum(n: int) -> int:
    return sum(int(c) for c in str(n))


class Numerology:
    def __init__(self, kb: KnowledgeStore, keep_masters_in_cycles: bool = True):
        nc = kb.numerology
        self._calc = nc["calculations"]
        policy = nc["default_policy"]
        self.masters: list[int] = policy["master_numbers"]
        system_id = policy["system"]
        system = nc["systems"][system_id]
        self.system_id = system_id
        self.letter_values: dict[str, int] = system["letter_values"]
        self.vowels: set[str] = set(system["vowels"])
        self.keep_masters_in_cycles = keep_masters_in_cycles

    # --- 基本還元(正本 reduction.decoz_component / master_number_stop) ---
    def reduce(self, n: int, keep_masters: bool = True) -> int:
        while n > 9:
            if keep_masters and n in self.masters:
                return n
            n = _digit_sum(n)
        return n

    def _rule(self, calc_id: str) -> dict:
        c = self._calc.get(calc_id)
        if c is None:
            raise KnowledgeGapError(f"numerology_core.calculations に {calc_id} が未定義")
        return c

    def _result(self, calc_id: str, value: int, **extra) -> dict:
        c = self._rule(calc_id)
        return {"value": value, "rule": calc_id, "label_ja": c.get("label_ja"),
                "source_ids": c.get("source_ids", []),
                "horse_status": c.get("horse_status"), **extra}

    # --- 出生系 ---
    def life_path(self, birth: date) -> dict:
        v = self.reduce(self.reduce(birth.month) + self.reduce(birth.day)
                        + self.reduce(_digit_sum(birth.year)))
        return self._result("life_path", v)

    def birthday_number(self, birth: date) -> dict:
        return self._result("birthday_number", self.reduce(birth.day))

    # --- 名前系(letter_valuesは正本) ---
    def _name_value(self, name: str, subset: str | None = None) -> int:
        total = 0
        for part in name.upper().split():
            part_sum = 0
            for ch in part:
                if ch not in self.letter_values:
                    continue
                if subset == "vowels" and ch not in self.vowels:
                    continue
                if subset == "consonants" and ch in self.vowels:
                    continue
                part_sum += self.letter_values[ch]
            total += self.reduce(part_sum) if part_sum else 0
        return self.reduce(total) if total else 0

    def expression(self, name_roman: str) -> dict:
        return self._result("expression", self._name_value(name_roman))

    def soul_urge(self, name_roman: str) -> dict:
        return self._result("soul_urge", self._name_value(name_roman, "vowels"))

    def personality(self, name_roman: str) -> dict:
        return self._result("personality", self._name_value(name_roman, "consonants"))

    # --- サイクル系(マスター保持は正本既定=保持。設定で切替=school_specific) ---
    def _creduce(self, n: int) -> int:
        return self.reduce(n, keep_masters=self.keep_masters_in_cycles)

    def personal_year(self, birth: date, target_year: int) -> dict:
        v = self._creduce(self.reduce(birth.month) + self.reduce(birth.day)
                          + self.reduce(_digit_sum(target_year)))
        return self._result("personal_year", v)

    def personal_month(self, py: int, target_month: int) -> dict:
        return self._result("personal_month", self._creduce(py + target_month))

    def personal_day(self, pm: int, target_day: int) -> dict:
        return self._result("personal_day", self._creduce(pm + self.reduce(target_day)))

    def universal_day(self, target: date) -> dict:
        v = self._creduce(_digit_sum(target.year) + _digit_sum(target.month)
                          + _digit_sum(target.day))
        return self._result("universal_day", v)

    # --- グループ相性(正本 compatibility.group_method) ---
    def group_of(self, kb: KnowledgeStore, number: int) -> str | None:
        base = number
        while base > 9:
            base = _digit_sum(base)
        groups = kb.numerology["compatibility"]["group_method"]["groups"]
        for gname, g in groups.items():
            if base in g["numbers"]:
                return gname
        return None

    def group_compat(self, kb: KnowledgeStore, a: int, b: int) -> dict:
        gm = kb.numerology["compatibility"]["group_method"]
        ga, gb = self.group_of(kb, a), self.group_of(kb, b)
        cond = ("same_number" if a == b else
                "same_group" if ga == gb else "different_group")
        for rule in gm["rules"]:
            if rule["if"] == cond:
                return {"condition": cond, "score": rule["score"],
                        "label_ja": rule["label_ja"], "groups": [ga, gb],
                        "status": gm["status"], "source_ids": gm["source_ids"],
                        "rule": "numerology.group_method"}
        raise KnowledgeGapError(f"group_method.rules に {cond} が未定義")
