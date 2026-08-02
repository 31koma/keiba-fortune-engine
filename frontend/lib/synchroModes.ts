// シンクロ度の表示モードエンジン。
// 「どの要素を含めて合成するか」を任意に選べる汎用再計算(synchro_v0の重みを再正規化)。
// 将来の「詳細設定(要素ON/OFF)」はMODESに新定義を足す or recompute()へ直接
// includeを渡すだけで対応できる。バックエンドAPIの components を入力とする。
import type { ApiSynchroComponents } from "./api";

/** 合成に使える要素(将来追加はここに増やす) */
export type ElementKey = "user_resonance" | "collective" | "harmony" | "day_flow";

export const ELEMENT_LABELS: Record<ElementKey, string> = {
  user_resonance: "あなた×馬の響き",
  collective: "集合意識(市場)の注目",
  harmony: "馬×騎手の調和",
  day_flow: "馬×レース日の流れ",
};

// synchro_v0.json weights.with_user の鏡写し(サブセット時は再正規化)
const BASE_WEIGHTS: Record<ElementKey, number> = {
  harmony: 0.30, day_flow: 0.25, user_resonance: 0.20, collective: 0.25,
};

export type Band = { tier: "gold" | "green" | "blue" | "orange" | "red"; label: string };

export function bandFor(score: number): Band {
  if (score >= 9) return { tier: "gold", label: "かなり流れが噛み合う日" };
  if (score >= 8) return { tier: "green", label: "流れが噛み合いやすい日" };
  if (score >= 6) return { tier: "blue", label: "噛み合わせ次第の日" };
  if (score >= 4) return { tier: "orange", label: "リズムの違いを楽しむ日" };
  return { tier: "red", label: "別々の流れの日" };
}

export type ModeResult = Band & {
  score: number;
  /** 実際に合成へ使われた要素(データが無い要素は自動で除外される) */
  used: { key: ElementKey; label: string; score: number; weight: number }[];
};

/** 指定要素のみでシンクロ度を再計算(重みは再正規化)。データ欠損要素は除外 */
export function recompute(
  components: ApiSynchroComponents, include: ElementKey[],
): ModeResult {
  const avail = include.filter((k) => components[k]?.score !== undefined);
  const wsum = avail.reduce((a, k) => a + BASE_WEIGHTS[k], 0);
  const used = avail.map((k) => ({
    key: k, label: ELEMENT_LABELS[k],
    score: components[k]!.score,
    weight: wsum > 0 ? BASE_WEIGHTS[k] / wsum : 0,
  }));
  const raw = used.reduce((a, u) => a + u.score * u.weight, 0);
  const score = Math.round(Math.min(10, raw) * 10) / 10;
  return { score, ...bandFor(score), used };
}

/** 表示モード定義(タブ)。将来「詳細設定」はincludeを動的に組めばよい */
export const MODES: Record<string, { label: string; include: ElementKey[]; desc: string }> = {
  you_quad: {
    label: "主",
    include: ["user_resonance", "collective", "harmony", "day_flow"],
    desc: "あなた・市場・馬・騎手・レース日を含めた総合評価です。",
  },
  quad: {
    label: "客",
    include: ["collective", "harmony", "day_flow"],
    desc: "市場・馬・騎手・レース日から見る客観評価です。",
  },
  market_compare: {
    label: "本",
    include: ["harmony", "day_flow"],  // 馬・騎手・レース日のみ(あなた・市場は除外)
    desc: "馬・騎手・レース日の調和だけを見る本質評価です。",
  },
};

export type MarketComparison = {
  pure: number;     // 純粋な流れ(馬・騎手・レース日のみ。あなた・市場は除外)
  market: number;   // 市場評価(オッズ由来)
  gap: number;      // 純粋な流れ - 市場評価
  headline: string;
  line: string;
};

/** 市場比較タブ用: 純粋な流れ×市場評価×差分と説明文(規則ベースの自動生成) */
export function marketComparison(components: ApiSynchroComponents): MarketComparison {
  const market = Math.round((components.collective?.score ?? 5) * 10) / 10;
  const pure = recompute(components, MODES.market_compare.include).score;
  const gap = Math.round((pure - market) * 10) / 10;
  let headline: string;
  let line: string;
  if (gap >= 2.5) {
    headline = "馬・騎手・当日の流れが、市場評価を大きく上回っています";
    line = "集合意識の視線はまだ薄いものの、純粋な流れは強く出ています。多くの人が見過ごしている物語かもしれません。";
  } else if (gap >= 1.0) {
    headline = "馬・騎手・当日の流れは、市場評価を上回っています";
    line = "オッズに表れた注目よりも、星と数字の流れが一歩先を行っています。";
  } else if (gap <= -2.5) {
    headline = "市場の期待が、純粋な流れを大きく上回っています";
    line = "集合意識は厚く支持していますが、純粋な流れは控えめです。期待と流れの温度差に注目です。";
  } else if (gap <= -1.0) {
    headline = "市場の期待が、純粋な流れをやや上回っています";
    line = "オッズの注目に対して、純粋な流れはひと呼吸置いた配置です。";
  } else {
    headline = "純粋な流れと市場評価がほぼ一致しています";
    line = "集合意識と星の流れが、同じ景色を見ている配置です。";
  }
  return { pure, market, gap, headline, line };
}
