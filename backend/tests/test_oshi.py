"""おすすめ(推し度)エンジンのテスト。合成入力のみ(実データ不使用)。

検証観点: 収束(調和平均)が平均と異なること、乖離ペナルティ、データ不足の明示、
ボーナス発火、上限クリップ、低スコア時に前向き理由を出さない誠実原則、
隠れ推しチップがスコアに影響しないこと、オッズ非依存。
"""
from app.domain.engine.oshi import OshiEngine


def _synchro(h, df, ur=None, col=None, df_cond="different", ur_cond=None):
    c = {"harmony": {"score": h}, "day_flow": {"score": df, "condition": df_cond}}
    if ur is not None:
        c["user_resonance"] = {"score": ur, "condition": ur_cond}
    if col is not None:
        c["collective"] = {"score": col}
    return {"components": c}


def _pn(score, signals=None, insufficient=False, confidence=1.0):
    return {"score": score, "signals": signals or {},
            "insufficient": insufficient, "confidence": confidence}


def test_convergence_beats_average_when_aligned():
    eng = OshiEngine()
    aligned = eng.compute(_synchro(8.0, 8.0), _pn(8.0))
    diverged = eng.compute(_synchro(10.0, 10.0), _pn(4.0))  # 平均は7だが乖離
    assert aligned["score"] > diverged["score"]
    assert diverged["score"] < 6.0  # 調和平均が乖離を罰する


def test_insufficient_choritsu_is_explicit():
    eng = OshiEngine()
    r = eng.compute(_synchro(6.0, 5.0), _pn(5.0, insufficient=True))
    assert r["confidence"] == "low"
    assert r["choritsu"] is None


def test_bonuses_and_cap():
    eng = OshiEngine()
    r = eng.compute(
        _synchro(10.0, 10.0, ur=10.0, ur_cond="same_number", df_cond="same_number"),
        _pn(10.0, {"rhythm": 10.0, "resilience": 10.0, "keynote": 10.0}))
    assert r["score"] == 10.0  # 上限クリップ
    assert any(b["id"] == "user_same_number" for b in r["bonuses"])


def test_low_score_has_no_positive_reasons():
    eng = OshiEngine()
    r = eng.compute(_synchro(9.0, 8.0), _pn(2.0))
    assert [x["id"] for x in r["reasons"]] == ["no_convergence"]


def test_hidden_chip_does_not_change_score():
    eng = OshiEngine()
    quiet = eng.compute(_synchro(8.5, 8.0, col=2.0), _pn(8.2, {"rhythm": 8.0}))
    loud = eng.compute(_synchro(8.5, 8.0, col=9.0), _pn(8.2, {"rhythm": 8.0}))
    assert quiet["score"] == loud["score"]  # オッズ非依存
    assert quiet["hidden"] is not None and loud["hidden"] is None


def test_confidence_tracks_choritsu_runs():
    eng = OshiEngine()
    full = eng.compute(_synchro(7.0, 7.0), _pn(7.0, confidence=1.0))
    med = eng.compute(_synchro(7.0, 7.0), _pn(7.0, confidence=0.6))
    low = eng.compute(_synchro(7.0, 7.0), _pn(7.0, confidence=0.2))
    none = eng.compute(_synchro(7.0, 7.0), _pn(5.0, insufficient=True))
    assert (full["confidence"], med["confidence"], low["confidence"],
            none["confidence"]) == ("full", "medium", "low", "low")


def test_adjusters_declared_but_not_scored_v0():
    eng = OshiEngine()
    r = eng.compute(_synchro(7.0, 7.0), _pn(7.0))
    assert r["adjusters"]["applied"] == []
    assert "track_bias" in r["adjusters"]["declared"]


def test_forbidden_hit_drops_line_not_500():
    """禁止語抵触は該当文だけ落として続行する(鑑定全体を500にしない)。"""
    from app.services.recommend import RecommendService

    class FakeFilter:
        disclaimer = "免責"
        def find(self, text):
            return ["上げ"] if "上げ" in text else []

    svc = RecommendService.__new__(RecommendService)  # __init__を通さず最小構成
    svc.filter = FakeFilter()
    oshi = {
        "reasons": [
            {"id": "rhythm_up", "line": "上げ局面にあたる配置です。"},
            {"id": "convergence", "line": "同じ方向を向いています。"},
        ],
        "hidden": {"label_ja": "隠れ推し", "line": "静かに重なっています。"},
        "framing": "上げを含む文言",
    }
    out = svc._narrate_oshi(oshi)
    assert [r["id"] for r in out["reasons"]] == ["convergence"]
    assert out["hidden"] is not None
    assert out["framing"] == "免責"
    assert set(out["filtered_out"]) == {"rhythm_up", "framing"}
