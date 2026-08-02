"""戦績数秘・調律理論(星読みターフ独自指標)— choritsu/1.0

既存の競馬理論・一般的な数秘術の模倣ではない、本プロジェクト独自の知的財産。
戦績(着順の並び)を波形として読み、「並びが次走へ向けて整いつつあるか」を
0〜10点で表す。結果の予測・保証ではなく、検証前の仮説指標(app_hypothesis)。

理論の核心 — 4信号:
  位相(phase)     : いまの流れの向き。減衰重み付きの質の傾き
  律(rhythm)      : 周期構造。自己相関で最良周期を検出し、その周期の続きとして
                    次走がどの局面(上げ/下げ)に当たるかを外挿する
  弾性(resilience): 崩れた後に戻る力。崩走直後の平均回復幅
  基調(keynote)   : 波の高さそのもの。減衰重み付きの質の平均

質変換 q(p) = (1/√p − 1/√18) / (1 − 1/√18):
  着順は等間隔ではない(1着と2着の差 > 11着と12着の差)を数式化した非線形写像。

設計方針(拡張性):
- 入力 PatternInput は features dict を持ち、人気・着差・レース間隔・距離/馬場
  変更などをキー追加のみで受け取れる(v1のスコアには着順のみ使用。
  人気は市場からの独立性と検証の循環論法回避のため意図的に不使用)
- 解析器は ANALYZERS レジストリのプラグイン方式。検証(verification_plan)後の
  重み更新・学習版は新versionを登録して切り替える(既存コード変更不要)
- データ不足(2走未満)は insufficient=True で明示し、値をでっち上げない
- 役割分担(2026-07-19確定): 本指標(UI表記「数」)は今後も戦績・波形・数理解析のみを
  担当する。ペース・バイアス・枠順・血統・馬場・距離・季節などの環境要因は
  ここへ入れず、oshi_v0(UI表記「収」)の adjusters レジストリ側で受ける
"""
import math
from dataclasses import dataclass, field

_QMIN = 1.0 / math.sqrt(18.0)


def quality(position: int) -> float:
    """着順→質 q∈[0,1]。1着=1.0、18着=0.0。非線形(上位ほど差が大きい)。"""
    p = max(1, min(18, position))
    return (1.0 / math.sqrt(p) - _QMIN) / (1.0 - _QMIN)


@dataclass
class PatternInput:
    """positions は新しい順の着順系列(異常走は除外済みであること)。"""
    positions: list[int]
    features: dict = field(default_factory=dict)  # popularity / intervals_days / ...
    source: str = "provider"


@dataclass
class PatternResult:
    score: float          # 0.0-10.0(insufficient時は5.0=中立)
    label: str
    signals: dict         # 信号名 -> 0.0-10.0
    confidence: float     # 0.0-1.0(v1.1: 使用走数/理想走数5)
    runs_used: int
    insufficient: bool
    version: str
    mock: bool
    source: str
    mode: str = "full"    # v1.1: full(4信号)/trio(律除く)/solo(基調のみ)/none


def band_label(score: float) -> str:
    if score >= 9.0:
        return "共振 — 並びが強く整っています"
    if score >= 8.0:
        return "調律 — リズムが噛み合いつつあります"
    if score >= 6.0:
        return "揺らぎ — 流れは中立です"
    if score >= 4.0:
        return "乱律 — リズムが乱れがちです"
    return "散逸 — 並びに方向性が見えません"


class TuningAnalyzerV1:
    """調律理論 v1(決定的・着順のみ)。"""

    version = "choritsu/1.0"
    mock = False
    MAX_RUNS = 8
    DECAY = 0.75          # 減衰率(1走古くなるごとに重み×0.75)
    SLUMP_Q = 0.35        # 崩走とみなす質の閾値(≈9着以下)

    @staticmethod
    def _clamp10(v: float) -> float:
        return max(0.0, min(10.0, v))

    def _weights(self, n: int) -> list[float]:
        w = [self.DECAY ** i for i in range(n)]  # 新しい順
        s = sum(w)
        return [x / s for x in w]

    # ---- 信号 ----
    def _phase(self, q: list[float]) -> float:
        """位相: 減衰重み付き傾き(直近が過去より高いか)。qは新しい順。"""
        n = len(q)
        w = self._weights(n - 1)
        # 隣接差分(新しい−古い)を減衰重みで平均。+1.0が最大級の上昇
        slope = sum((q[i] - q[i + 1]) * w[i] for i in range(n - 1))
        return self._clamp10(5.0 + slope * 12.0)

    def _rhythm(self, q: list[float]) -> float:
        """律: lag1-3の自己相関で最良周期を検出し、周期の続きが上げ局面なら加点。"""
        n = len(q)
        if n < 4:
            return 5.0
        mu = sum(q) / n
        var = sum((x - mu) ** 2 for x in q) or 1e-9
        best_lag, best_ac = 0, 0.0
        for lag in (1, 2, 3):
            if n - lag < 2:
                continue
            ac = sum((q[i] - mu) * (q[i + lag] - mu) for i in range(n - lag)) / var
            if abs(ac) > abs(best_ac):
                best_lag, best_ac = lag, ac
        if best_lag == 0:
            return 5.0
        # 周期の続きとして「次走」を外挿: 次走位置 = -1 ≡ (best_lag - 1) 走前と同位相
        anchor = q[best_lag - 1]
        direction = anchor - mu  # 同位相の走が平均より上なら上げ局面
        strength = min(1.0, abs(best_ac))
        return self._clamp10(5.0 + direction * strength * 10.0)

    def _resilience(self, q: list[float]) -> float:
        """弾性: 崩走(q<閾値)の直後にどれだけ戻したか。崩走が無ければ中立+安定加点。"""
        rebounds = []
        # qは新しい順: q[i+1]が崩走→q[i]がその次の走
        for i in range(len(q) - 1):
            if q[i + 1] < self.SLUMP_Q:
                rebounds.append(q[i] - q[i + 1])
        if not rebounds:
            return self._clamp10(6.0 + (min(q) - self.SLUMP_Q) * 5.0)  # 崩れ知らず
        return self._clamp10(5.0 + (sum(rebounds) / len(rebounds)) * 10.0)

    def _keynote(self, q: list[float]) -> float:
        """基調: 減衰重み付きの質の平均(いまの地力の波の高さ)。"""
        w = self._weights(len(q))
        return self._clamp10(sum(x * wi for x, wi in zip(q, w)) * 10.0)

    # ---- 合成 ----
    W = {"phase": 0.32, "rhythm": 0.22, "resilience": 0.18, "keynote": 0.28}

    def analyze(self, inp: PatternInput) -> PatternResult:
        pos = [p for p in inp.positions if 1 <= p <= 18][: self.MAX_RUNS]
        runs = len(pos)
        if runs < 2:
            return PatternResult(
                score=5.0, label="未律 — 読むには走歴が足りません",
                signals={}, confidence=runs / self.MAX_RUNS, runs_used=runs,
                insufficient=True, version=self.version, mock=self.mock,
                source=inp.source)
        q = [quality(p) for p in pos]
        signals = {
            "phase": round(self._phase(q), 2),
            "rhythm": round(self._rhythm(q), 2),
            "resilience": round(self._resilience(q), 2),
            "keynote": round(self._keynote(q), 2),
        }
        score = round(self._clamp10(sum(signals[k] * self.W[k] for k in self.W)), 1)
        return PatternResult(
            score=score, label=band_label(score), signals=signals,
            confidence=round(min(1.0, runs / self.MAX_RUNS), 2), runs_used=runs,
            insufficient=False, version=self.version, mock=self.mock,
            source=inp.source)


class TuningAnalyzerV11(TuningAnalyzerV1):
    """調律理論 v1.1 — 適応解析。

    理想窓=直近5走。データ数に応じて解析を切り替え、1走でも読める:
      4-5走 : full(位相・律・弾性・基調の4信号)
      2-3走 : trio(自己相関が不定になる律を除いた3信号。重みは再正規化)
      1走   : solo(基調のみ)
      0走   : insufficient(解析不能=データが1走も無い場合のみ)
    信頼度 confidence = min(1, 走数/5)。
    縮約: score = 5.0 + (raw - 5.0) × confidence。少データほど中立へ寄せ、
    1走の好走だけで満点級が出る過信を防ぐ(値をでっち上げない誠実原則の数式化)。
    """

    version = "choritsu/1.1"
    IDEAL_RUNS = 5
    MAX_RUNS = 5          # 理想窓: 6走以上あっても直近5走を読む

    _SIGNAL_FNS = ("phase", "rhythm", "resilience", "keynote")

    def _mode_for(self, runs: int) -> tuple[str, list[str]]:
        if runs >= 4:
            return "full", ["phase", "rhythm", "resilience", "keynote"]
        if runs >= 2:
            return "trio", ["phase", "resilience", "keynote"]
        return "solo", ["keynote"]

    def analyze(self, inp: PatternInput) -> PatternResult:
        pos = [p for p in inp.positions if 1 <= p <= 18][: self.MAX_RUNS]
        runs = len(pos)
        if runs == 0:
            return PatternResult(
                score=5.0, label="未律 — まだ読める走歴がありません",
                signals={}, confidence=0.0, runs_used=0,
                insufficient=True, version=self.version, mock=self.mock,
                source=inp.source, mode="none")
        q = [quality(p) for p in pos]
        mode, keys = self._mode_for(runs)
        fns = {"phase": self._phase, "rhythm": self._rhythm,
               "resilience": self._resilience, "keynote": self._keynote}
        signals = {k: round(fns[k](q), 2) for k in keys}
        wsum = sum(self.W[k] for k in keys)
        raw = sum(signals[k] * self.W[k] for k in keys) / wsum
        confidence = round(min(1.0, runs / self.IDEAL_RUNS), 2)
        score = round(self._clamp10(5.0 + (raw - 5.0) * confidence), 1)
        return PatternResult(
            score=score, label=band_label(score), signals=signals,
            confidence=confidence, runs_used=runs,
            insufficient=False, version=self.version, mock=self.mock,
            source=inp.source, mode=mode)


# ---- 解析器レジストリ(検証後のv2・学習版はここに追加して切替) ----
ANALYZERS: dict[str, TuningAnalyzerV1] = {
    "choritsu/1.0": TuningAnalyzerV1(),
    "choritsu/1.1": TuningAnalyzerV11(),
}
DEFAULT_ANALYZER = "choritsu/1.1"

MODE_LABELS_JA = {
    "full": "全律(4信号)",
    "trio": "三律(律を除く3信号)",
    "solo": "単律(基調のみ)",
    "none": "未律",
}

SIGNAL_LABELS_JA = {
    "phase": "位相(流れの向き)",
    "rhythm": "律(周期の続き)",
    "resilience": "弾性(戻る力)",
    "keynote": "基調(波の高さ)",
}


def analyze(positions: list[int] | None, features: dict | None = None,
            analyzer: str = DEFAULT_ANALYZER) -> PatternResult:
    """着順系列(新しい順)を解析。系列が無い場合はデータ不足として中立を返す。"""
    inp = PatternInput(positions or [], features or {},
                       source="provider" if positions else "none")
    return ANALYZERS[analyzer].analyze(inp)
