// 今日のシンクロ度 v0(フロント暫定実装)。
// 規則は backend/app/knowledge/proposals/synchro_v0.json(正本v1.3収録候補・
// app_hypothesis)の鏡写し。正式実装では GET /v1/day-recommendations へ置換する。
// オッズ=集合意識(市場に集まる注目)の近似であり、勝率・結果予測ではない。
import { MOCK_RACES, MockEntry, MockRace } from "./mock";
import { lifePath, personalDay, sunSign } from "./preview";

const digits = (n: number) => String(n).split("").reduce((a, c) => a + +c, 0);
const baseN = (n: number) => { while (n > 9) n = digits(n); return n; };
const reduce = (n: number) => { while (n > 9 && ![11, 22, 33].includes(n)) n = digits(n); return n; };
export const universalDay = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return reduce(digits(y) + digits(m) + digits(d));
};

const GROUPS: Record<string, number[]> = {
  independent: [1, 5, 7], practical: [2, 4, 8], harmonious: [3, 6, 9],
};
const groupOf = (n: number) => Object.keys(GROUPS).find((g) => GROUPS[g].includes(baseN(n)))!;

// ---- 星座index・元素(preview.SIGNSと同順) ----
const SIGN_ELEMS: Record<string, [number, string]> = {
  Aries: [1, "fire"], Taurus: [2, "earth"], Gemini: [3, "air"], Cancer: [4, "water"],
  Leo: [5, "fire"], Virgo: [6, "earth"], Libra: [7, "air"], Scorpio: [8, "water"],
  Sagittarius: [9, "fire"], Capricorn: [10, "earth"], Aquarius: [11, "air"], Pisces: [12, "water"],
};
const HARMONIOUS_ELEM: Record<string, string> = { fire: "air", air: "fire", earth: "water", water: "earth" };
// distance法プレビュー(0=同座,4=トライン強調。正式値は正本distance_table)
const DIST_SCORE = [3, 1.5, 2.5, 1.5, 3, 1, 2];

// ---- 規則定数(synchro_v0.jsonの鏡写し) ----
const W_USER = { harmony: 0.30, day_flow: 0.25, user_resonance: 0.20, collective: 0.25 };
const W_NO_USER = { harmony: 0.375, day_flow: 0.3125, collective: 0.3125 };
const DAY_FLOW_MAP = { same_number: 10, same_group: 7.5, different: 4.5 };
const USER_MAP = { same_number: 10, same_group: 8, universal_match: 6, different: 4.5 };
const TH = { flowHigh: 7.0, flowLow: 5.5, attHigh: 7.0, attLow: 5.0 };

export type SyncPattern = {
  type: "resonance" | "hidden" | "heat" | "quiet";
  label: string;
  line: string;
};
const PATTERNS: Record<SyncPattern["type"], Omit<SyncPattern, "type">> = {
  resonance: { label: "共鳴", line: "集合意識の注目と占術の流れが、同じ方向を向いている配置です。" },
  hidden: { label: "隠れシンクロ", line: "集合意識の注目は薄いものの、占術の流れは強い一頭です。多くの人がまだ見過ごしている物語がここにあります。" },
  heat: { label: "過熱", line: "集合意識の注目が先行している配置です。占術の流れは控えめで、期待と流れの間に温度差があります。" },
  quiet: { label: "静観", line: "集合意識・占術ともに静かな配置です。一歩引いて全体を眺めたい組み合わせです。" },
};

export type Synchro = {
  score: number; tier: "gold" | "green" | "blue" | "orange" | "red"; label: string;
  flow: number; attention: number; supportShare: number | null;
  pattern: SyncPattern;
  components: { harmony: number; dayFlow: number; userResonance: number | null; collective: number };
};

const norm13 = (raw: number) => (raw - 1) / 2 * 10;

function harmony(horseBirth: string, jockeyBirth: string): number {
  const hs = SIGN_ELEMS[sunSign(horseBirth).en];
  const js = SIGN_ELEMS[sunSign(jockeyBirth).en];
  const dist = Math.min(Math.abs(hs[0] - js[0]), 12 - Math.abs(hs[0] - js[0]));
  const elem = hs[1] === js[1] || HARMONIOUS_ELEM[hs[1]] === js[1] ? 3 : 1;
  const zc = 0.6 * DIST_SCORE[dist] + 0.4 * elem; // 1..3
  const hl = lifePath(horseBirth), jl = lifePath(jockeyBirth);
  const gc = hl === jl ? 3 : groupOf(hl) === groupOf(jl) ? 2 : 1; // 1..3
  return (norm13(zc) + norm13(gc)) / 2;
}

/** オッズ→集合意識の注目度0..10(s=0.8/odds を対数尺度化)。未取得は中立5.0 */
export function collectiveAttention(winOdds: number | null | undefined): { att: number; s: number | null } {
  if (!winOdds || winOdds <= 0) return { att: 5.0, s: null };
  const s = Math.max(0.01, Math.min(0.95, 0.8 / winOdds));
  return { att: Math.max(0, Math.min(10, 5 * Math.log10(100 * s))), s };
}

export function computeSynchro(
  entry: MockEntry, race: MockRace, userBirth: string | null,
): Synchro {
  const har = harmony(entry.horseBirth, entry.jockeyBirth);
  const pd = personalDay(entry.horseBirth, race.date);
  const ud = universalDay(race.date);
  const dayFlow = pd === ud ? DAY_FLOW_MAP.same_number
    : groupOf(pd) === groupOf(ud) ? DAY_FLOW_MAP.same_group : DAY_FLOW_MAP.different;

  let userRes: number | null = null;
  if (userBirth) {
    const upd = personalDay(userBirth, race.date);
    userRes = upd === pd ? USER_MAP.same_number
      : groupOf(upd) === groupOf(pd) ? USER_MAP.same_group
        : groupOf(upd) === groupOf(ud) ? USER_MAP.universal_match : USER_MAP.different;
  }

  const { att, s } = collectiveAttention(entry.winOdds);
  let total: number, flow: number;
  if (userRes !== null) {
    total = har * W_USER.harmony + dayFlow * W_USER.day_flow
      + userRes * W_USER.user_resonance + att * W_USER.collective;
    flow = (har * W_USER.harmony + dayFlow * W_USER.day_flow + userRes * W_USER.user_resonance)
      / (W_USER.harmony + W_USER.day_flow + W_USER.user_resonance);
  } else {
    total = har * W_NO_USER.harmony + dayFlow * W_NO_USER.day_flow + att * W_NO_USER.collective;
    flow = (har * W_NO_USER.harmony + dayFlow * W_NO_USER.day_flow)
      / (W_NO_USER.harmony + W_NO_USER.day_flow);
  }
  const score = Math.round(Math.min(10, total) * 10) / 10;

  const ptype: SyncPattern["type"] =
    flow >= TH.flowHigh && att >= TH.attHigh ? "resonance"
      : flow >= TH.flowHigh && att < TH.attLow ? "hidden"
        : flow < TH.flowLow && att >= TH.attHigh ? "heat" : "quiet";

  const tier = score >= 9 ? "gold" : score >= 8 ? "green" : score >= 6 ? "blue"
    : score >= 4 ? "orange" : "red";
  const label = score >= 9 ? "かなり流れが噛み合う日"
    : score >= 8 ? "流れが噛み合いやすい日"
      : score >= 6 ? "噛み合わせ次第の日"
        : score >= 4 ? "リズムの違いを楽しむ日" : "別々の流れの日";

  return {
    score, tier, label,
    flow: Math.round(flow * 100) / 100,
    attention: Math.round(att * 100) / 100,
    supportShare: s,
    pattern: { type: ptype, ...PATTERNS[ptype] },
    components: { harmony: Math.round(har * 100) / 100, dayFlow, userResonance: userRes, collective: Math.round(att * 100) / 100 },
  };
}

export type RecommendItem = {
  race: MockRace; entry: MockEntry; synchro: Synchro;
};

const PATTERN_PRIORITY: Record<string, number> = { hidden: 0, resonance: 1, quiet: 2, heat: 3 };

/** 今日のおすすめ: 全出走をシンクロ度降順(タイブレーク: hidden > resonance > その他) */
export function dayRecommendations(userBirth: string | null): RecommendItem[] {
  const items: RecommendItem[] = [];
  for (const race of MOCK_RACES) {
    for (const entry of race.entries) {
      items.push({ race, entry, synchro: computeSynchro(entry, race, userBirth) });
    }
  }
  items.sort((a, b) =>
    b.synchro.score - a.synchro.score
    || PATTERN_PRIORITY[a.synchro.pattern.type] - PATTERN_PRIORITY[b.synchro.pattern.type]
    || a.race.number - b.race.number
    || a.entry.post - b.entry.post);
  return items;
}

export const SYNC_FRAMING =
  "おすすめ=占術と集合意識(オッズ)の共鳴が強い組み合わせ。馬券購入の推奨ではなく、観戦の視点の提案です。";
