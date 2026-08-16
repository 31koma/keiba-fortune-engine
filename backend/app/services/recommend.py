"""今日のおすすめユースケース。

対象日の全出走のシンクロ度(synchro_v0)・調律(choritsu)・推し度(oshi_v0)を計算し、
推し度降順に提示(2026-07-19より最終評価=推し度で統一)。
タイブレークは規則recommendation.desc準拠(hidden > resonance > その他 → R番・馬番昇順)。
文言は規則JSON由来+禁止語フィルタ必須。おすすめ=観戦の視点の提案であり、
馬券購入の推奨・結果予測ではない(この位置づけ自体を応答に含める)。
"""
from datetime import date

from app.domain.engine import pattern_numerology
from app.domain.engine.oshi import OshiEngine
from app.domain.engine.synchro import SynchroEngine
from app.domain.engine.wordfilter import ForbiddenFilter
from app.providers.base import DataProviderSet

_PATTERN_PRIORITY = {"hidden": 0, "resonance": 1, "quiet": 2, "heat": 3}


class RecommendService:
    def __init__(self, synchro: SynchroEngine, ffilter: ForbiddenFilter,
                 provider: DataProviderSet, oshi: OshiEngine | None = None):
        self.synchro = synchro
        self.filter = ffilter
        self.provider = provider
        self.oshi = oshi or OshiEngine()

    def _safe_framing(self, text: str) -> str:
        return self.filter.disclaimer if self.filter.find(text) else text

    def _narrate_oshi(self, oshi: dict) -> dict:
        """おすすめの語り文へ禁止語検査を適用する。

        鑑定文生成(textgen)と異なり、おすすめの理由文は装飾であって鑑定の本体では
        ないため、抵触時はreject(500)せず該当文だけを落として提示を続行する
        (1文の抵触で当日全馬の鑑定が止まるのを防ぐ)。落とした場合はIDを
        filtered_out に記録し、正本の禁止語リストとの照合・文言修正に使う。
        """
        dropped: list[str] = []
        kept = []
        for r in oshi["reasons"]:
            if self.filter.find(r["line"]):
                dropped.append(r["id"])
            else:
                kept.append(r)
        oshi["reasons"] = kept
        if oshi["hidden"] and self.filter.find(oshi["hidden"]["line"]):
            dropped.append("hidden_chip")
            oshi["hidden"] = None
        if self.filter.find(oshi["framing"]):
            dropped.append("framing")
            oshi["framing"] = self.filter.disclaimer
        oshi["filtered_out"] = dropped
        return oshi

    def day_recommendations(self, target: date, user_birth: date | None,
                            provider_credit: dict) -> dict:
        races = self.provider.list_races(target)
        items: list[dict] = []
        for race in races:
            for entry in race.entries:
                horse = self.provider.get_horse(entry.horse_id)
                jockey = self.provider.get_jockey(entry.jockey_id)
                if horse is None or jockey is None:
                    continue
                sync = self.synchro.compute(horse, jockey, race, target,
                                            entry.win_odds, user_birth)
                sync["pattern"]["line"] = self.filter.apply(sync["pattern"]["line"])
                # 戦績数秘・調律理論(独自指標。着順系列が無い馬はデータ不足を明示)
                pn = pattern_numerology.analyze(
                    self.provider.get_recent_positions(entry.horse_id))
                pn_dict = {
                    "score": pn.score, "signals": pn.signals,
                    "insufficient": pn.insufficient, "confidence": pn.confidence,
                }
                oshi = self._narrate_oshi(self.oshi.compute(sync, pn_dict))
                items.append({
                    "race_id": race.internal_id,
                    "race_name": race.race_name,
                    "race_number": race.race_number,
                    "racecourse": race.racecourse,
                    "start_time": race.start_time,
                    "distance": race.distance,
                    "surface": race.surface,
                    "head_count": len(race.entries),
                    "post_number": entry.post_number,
                    "horse_id": horse.internal_id,
                    "horse_name": horse.registered_name,
                    "jockey_id": jockey.internal_id,
                    "jockey_name": jockey.name,
                    "win_odds": entry.win_odds,
                    "physical": getattr(entry, "physical", None),
                    "synchro": sync,
                    "pattern_numerology": {
                        "score": pn.score, "label": pn.label, "signals": pn.signals,
                        "confidence": pn.confidence, "runs_used": pn.runs_used,
                        "insufficient": pn.insufficient,
                        "version": pn.version, "mock": pn.mock, "source": pn.source,
                        "mode": pn.mode,
                    },
                    "oshi": oshi,
                })

        items.sort(key=lambda it: (
            -it["oshi"]["score"],
            _PATTERN_PRIORITY.get(it["synchro"]["pattern"]["type"], 9),
            it["race_number"],
            it["post_number"] or 0,
        ))

        rules_meta = self.synchro.rules["meta"]
        # 看板(この日のおすすめ)は確信度low(走歴1走以下)を避ける(規則recommendation.desc)
        reco = next((it for it in items if it["oshi"]["confidence"] != "low"),
                    items[0] if items else None)
        return {
            "target_date": target.isoformat(),
            "user_included": user_birth is not None,
            "recommendation": reco,
            "items": items,
            "framing": self._safe_framing(
                self.oshi.rules["recommendation"]["framing_ja"]),
            "rule": "oshi_v0",
            "per_item_rule": "synchro_score_v0",
            "hypothesis_status": rules_meta["status"],
            "validation_status": rules_meta["validation"],
            "disclaimer": self.filter.disclaimer,
            "provider_credit": provider_credit,
        }
