"""おすすめ(推し度)エンジン — oshi/1.0

星読みターフ全体の最終評価。核は「収束」: 由来の異なる独立レンズ——
本質(純占術: 馬×騎手の調和+馬×レース日の流れ)と調律(戦績の波形)——が
同じ方向を向いたときにだけ高くなる(調和平均。平均ではない)。

ただし収束=おすすめの全てではない。規則JSON(knowledge/proposals/oshi_v0.json)の
adjusters レジストリに宣言した独立要素(枠順・トラックバイアス・ペース・血統・馬場)を、
検証(verification_runs)で有効性が確認されたものから段階的に組み込む設計とする
(weight変更+新version登録のみ。コード変更不要)。

オッズ(集合意識)はスコアに使用しない。人気ベースラインと比較する検証可能性を
保つためであり、集合意識は「隠れ推し」の物語チップとしてのみ参照する。
規則・重み・文言はJSONが持ち、コードは計算手順のみを持つ(憲章第2条)。
検証前の仮説指標(app_hypothesis)。結果の予測・保証ではない。
"""
import json
from pathlib import Path

PROPOSAL_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "proposals" / "oshi_v0.json"


def load_rules(path: Path | None = None) -> dict:
    p = path or PROPOSAL_PATH
    return json.loads(p.read_text(encoding="utf-8"))


class OshiEngine:
    def __init__(self, rules: dict | None = None):
        self.rules = rules or load_rules()

    # ---------- 条件評価(kindごとの手順のみ。閾値・意味はJSONが持つ) ----------
    def _fires(self, when: dict, ctx: dict) -> bool:
        kind = when.get("kind")
        if kind == "signal_at_least":
            sig = ctx["signals"].get(when["signal"])
            return sig is not None and sig >= when["threshold"]
        if kind == "component_at_least":
            comp = ctx["components"].get(when["component"])
            return comp is not None and comp.get("score", 0.0) >= when["threshold"]
        if kind == "user_condition_in":
            return ctx["user_condition"] in when["conditions"]
        if kind == "day_flow_condition_in":
            return ctx["day_flow_condition"] in when["conditions"]
        if kind == "convergence":
            e, c = ctx["essence"], ctx["choritsu"]
            return (c is not None and abs(e - c) <= when["max_gap"]
                    and min(e, c) >= when["min_both"])
        if kind == "fallback":
            return True
        return False

    # ---------- 合成 ----------
    def compute(self, synchro: dict, pattern_numerology: dict | None) -> dict:
        comps = synchro["components"]
        ew = self.rules["core"]["essence_weights"]
        essence = sum(comps[k]["score"] * ew[k] for k in ew) / sum(ew.values())

        pn = pattern_numerology or {}
        insufficient = bool(pn.get("insufficient", True))
        choritsu = None if insufficient else float(pn["score"])

        if choritsu is None:
            base = essence
            confidence = self.rules["core"]["choritsu_insufficient"]["confidence"]
        else:
            base = (2.0 * essence * choritsu / (essence + choritsu)
                    if (essence + choritsu) > 0 else 0.0)
            cb = self.rules["core"]["confidence_bands"]
            cc = float(pn.get("confidence", 1.0))
            if cc >= cb["full"]:
                confidence = "full"
            elif cc >= cb["medium"]:
                confidence = "medium"
            else:
                confidence = "low"

        ctx = {
            "essence": essence,
            "choritsu": choritsu,
            "signals": pn.get("signals") or {},
            "components": comps,
            "user_condition": (comps.get("user_resonance") or {}).get("condition"),
            "day_flow_condition": (comps.get("day_flow") or {}).get("condition"),
        }

        bonuses = [
            {"id": b["id"], "label_ja": b["label_ja"], "add": b["add"]}
            for b in self.rules["bonuses"] if self._fires(b["when"], ctx)
        ]
        score = round(min(10.0, base + sum(b["add"] for b in bonuses)), 1)

        rz = self.rules["reasons"]
        reasons = []
        positive_ok = score >= rz.get("positive_min_score", 0.0)
        for t in rz["templates"]:
            if len(reasons) >= rz["max_reasons"]:
                break
            if t["when"].get("kind") == "fallback":
                continue  # fallbackは最後に、他が無い場合のみ
            if positive_ok and self._fires(t["when"], ctx):
                reasons.append({"id": t["id"], "line": t["line"]})
        if not reasons:
            fb = next((t for t in rz["templates"]
                       if t["when"].get("kind") == "fallback"), None)
            if fb:
                reasons.append({"id": fb["id"], "line": fb["line"]})

        hc = self.rules["hidden_chip"]
        attention = (comps.get("collective") or {}).get("score")
        hidden = None
        if (attention is not None and attention < hc["attention_below"]
                and score >= hc["score_at_least"]):
            hidden = {"label_ja": hc["label_ja"], "line": hc["line"]}

        band = next(b for b in self.rules["score_bands"] if score >= b["min"])
        slots = self.rules["adjusters"]["slots"]
        return {
            "score": score,
            "tier": band["tier"],
            "label": band["label_ja"],
            "essence": round(essence, 2),
            "choritsu": choritsu,
            "base": round(base, 2),
            "confidence": confidence,
            "bonuses": bonuses,
            "reasons": reasons,
            "hidden": hidden,
            "adjusters": {
                "applied": [s["id"] for s in slots if s["weight"] > 0],
                "declared": [s["id"] for s in slots],
            },
            "version": self.rules["meta"]["version"],
            "rule": "oshi_v0(app_hypothesis)",
            "hypothesis_status": self.rules["meta"]["status"],
            "validation_status": self.rules["meta"]["validation"],
            "framing": self.rules["framing_ja"],
        }
