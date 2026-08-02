// バックエンドAPI(FastAPI)クライアント。
// API不達時はnullを返し、呼び出し側がMock表示へフォールバックする。
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type ApiPattern = {
  type: "resonance" | "hidden" | "heat" | "quiet";
  label_ja: string;
  line: string;
};

export type ApiSynchro = {
  score: number;
  tier: "gold" | "green" | "blue" | "orange" | "red";
  label: string;
  flow: number;
  pattern: ApiPattern;
  hypothesis_status: string;
  validation_status: string;
};

export type ApiSynchroComponents = {
  harmony?: { score: number };
  day_flow?: { score: number };
  user_resonance?: { score: number };
  collective?: { score: number; win_odds?: number | null; support_share?: number | null };
};

export type ApiPatternNumerology = {
  score: number;
  label: string;
  signals: Record<string, number>;
  confidence: number;
  runs_used: number;
  insufficient: boolean;
  version: string;
  mock: boolean;
  source: string;
  mode?: "full" | "trio" | "solo" | "none";
};

export type ApiOshi = {
  score: number;
  tier: "gold" | "green" | "blue" | "orange" | "red";
  label: string;
  essence: number;
  choritsu: number | null;
  base: number;
  confidence: "full" | "medium" | "low";
  bonuses: { id: string; label_ja: string; add: number }[];
  reasons: { id: string; line: string }[];
  hidden: { label_ja: string; line: string } | null;
  adjusters: { applied: string[]; declared: string[] };
  version: string;
  rule: string;
  hypothesis_status: string;
  validation_status: string;
  framing: string;
};

export type ApiRecoItem = {
  race_id: string;
  race_name: string;
  race_number: number;
  racecourse: string;
  start_time: string | null;
  distance: number;
  surface: string;
  head_count: number;
  post_number: number | null;
  horse_id: string;
  horse_name: string;
  jockey_id: string;
  jockey_name: string;
  win_odds: number | null;
  synchro: ApiSynchro & { components: ApiSynchroComponents };
  pattern_numerology?: ApiPatternNumerology;
  oshi?: ApiOshi;
};

export type ApiDayRecommendations = {
  target_date: string;
  user_included: boolean;
  recommendation: ApiRecoItem | null;
  items: ApiRecoItem[];
  framing: string;
  disclaimer: string;
  provider_credit: { data_provider_name: string; data_provider_credit: string };
};

export async function fetchDayRecommendations(
  userBirth: string | null, targetDate?: string,
): Promise<ApiDayRecommendations | null> {
  const q = new URLSearchParams();
  if (userBirth) q.set("user_birth_date", userBirth);
  if (targetDate) q.set("target_date", targetDate);
  try {
    const r = await fetch(`${API_BASE}/v1/day-recommendations?${q}`,
      { cache: "no-store" });
    if (!r.ok) return null;
    const body = await r.json();
    if (!body || !Array.isArray(body.items)) return null;
    return body as ApiDayRecommendations;
  } catch {
    return null;
  }
}

/** レース単位にまとめる(items はスコア降順で届くので、レース内もその順) */
export type ApiRaceGroup = {
  race_id: string;
  racecourse: string;
  race_number: number;
  race_name: string;
  items: ApiRecoItem[];
};

export function groupByRace(items: ApiRecoItem[]): ApiRaceGroup[] {
  const map = new Map<string, ApiRaceGroup>();
  for (const it of items) {
    let g = map.get(it.race_id);
    if (!g) {
      g = { race_id: it.race_id, racecourse: it.racecourse,
        race_number: it.race_number, race_name: it.race_name, items: [] };
      map.set(it.race_id, g);
    }
    g.items.push(it);
  }
  return Array.from(map.values())
    .sort((a, b) => a.racecourse.localeCompare(b.racecourse, "ja")
      || a.race_number - b.race_number);
}

export const raceTitle = (g: { racecourse: string; race_number: number; race_name: string }) =>
  g.race_name && g.race_name !== "レース"
    ? `${g.race_name}(${g.racecourse}${g.race_number}R)`
    : `${g.racecourse}${g.race_number}R`;

/** JRA式の枠番割当(8枠・多頭数は大きい枠から複数頭) */
export function wakuOf(post: number, headCount: number): number {
  if (headCount <= 8) return Math.min(post, 8);
  const base = Math.floor(headCount / 8);
  const extra = headCount % 8;
  let cum = 0;
  for (let f = 1; f <= 8; f++) {
    cum += base + (f > 8 - extra ? 1 : 0);
    if (post <= cum) return f;
  }
  return 8;
}

export const WAKU_STYLE: Record<number, { bg: string; fg: string; border?: string }> = {
  1: { bg: "#ffffff", fg: "#1a1a1a", border: "#999" },
  2: { bg: "#1a1a1a", fg: "#ffffff" },
  3: { bg: "#d63c3c", fg: "#ffffff" },
  4: { bg: "#2b5fc7", fg: "#ffffff" },
  5: { bg: "#f2d43c", fg: "#1a1a1a" },
  6: { bg: "#3c9e50", fg: "#ffffff" },
  7: { bg: "#e8862f", fg: "#ffffff" },
  8: { bg: "#f2a0c0", fg: "#1a1a1a" },
};

// ---------- 過去レース(検証用の読み取り専用ビュー) ----------
export type ApiPastRaceSummary = {
  race_id: string;
  racecourse: string;
  race_number: number;
  race_name: string;
  distance: number;
  surface: string;          // 芝 / ダート / 障害
  start_time: string | null;
  head_count: number;
  grade: string | null;
  has_results: boolean;     // SED(確定成績)があるか
  has_snapshot: boolean;    // レース前に保存された評価があるか
};

export type ApiPastDay = { date: string; races: ApiPastRaceSummary[] };

export type ApiPastRaces = { days: ApiPastDay[]; framing: string };

export type ApiPastResultRow = {
  chaku: number | null;     // 確定着順(異常時はnull)
  post_number: number | null;
  horse_id: string;
  horse_name: string;
  ninki: number | null;
  odds_final: number | null;
  status: string | null;    // 出走取消・競走除外など(正常時はnull)
};

export type ApiPastSnapshotItem = {
  rank: number;             // 星読み順位(スナップショット内の代表スコア順)
  post_number: number | null;
  horse_id: string;
  horse_name: string;
  jockey_name: string;
  win_odds: number | null;
  score: number;
  tier: string;
  label: string;
  confidence: "full" | "medium" | "low" | null;
  chaku: number | null;     // 確定着順(結果未確定・異常時はnull)
  status: string | null;
};

export type ApiPastSnapshot = {
  saved_at: string;         // 保存日時(JST)
  rules_ver: string | null;
  engine_ver: string;
  metric: "oshi" | "synchro";
  metric_label: string;     // 収束度 / シンクロ度
  items: ApiPastSnapshotItem[];
};

export type ApiPastVerification = {
  top1_chaku: number | null;
  top1_in_top3: boolean | null;
  top3_in_top3: number;
  winner_rank: number | null;
  winner_ninki: number | null;
};

export type ApiPastRaceDetail = {
  race: {
    race_id: string;
    date: string;
    racecourse: string;
    race_number: number;
    race_name: string;
    distance: number;
    surface: string;
    start_time: string | null;
    head_count: number;
    grade: string | null;
  };
  results: ApiPastResultRow[] | null;
  snapshot: ApiPastSnapshot | null;
  snapshot_note: string | null;
  verification: ApiPastVerification | null;
  framing: string;
};

export async function fetchPastRaces(): Promise<ApiPastRaces | null> {
  try {
    const r = await fetch(`${API_BASE}/v1/past-races`, { cache: "no-store" });
    if (!r.ok) return null;
    const body = await r.json();
    if (!body || !Array.isArray(body.days)) return null;
    return body as ApiPastRaces;
  } catch {
    return null;
  }
}

export async function fetchPastRaceDetail(
  raceId: string,
): Promise<ApiPastRaceDetail | null> {
  try {
    const r = await fetch(`${API_BASE}/v1/past-races/${raceId}`,
      { cache: "no-store" });
    if (!r.ok) return null;
    return (await r.json()) as ApiPastRaceDetail;
  } catch {
    return null;
  }
}

// ---------- あなたの運の流れ(年運・月運・日運) ----------
export type ApiCycleMeanings = {
  keywords_ja: string[];
  positive: string | null;
  negative: string | null;
};

export type ApiCycle = {
  value: number;
  year_theme: string;
  month_theme: string;
  day_theme: string;
  status?: string;
  meanings?: ApiCycleMeanings;
};

export type ApiHumanFortune = {
  target_date: string;
  personal_year: ApiCycle;
  personal_month: ApiCycle;
  personal_day: ApiCycle;
  universal_day: ApiCycle & { applies_to?: string };
  interpretation_parts: {
    foreground_day: { number: number; role_ja: string };
    middle_month: { number: number; role_ja: string };
    background_year: { number: number; role_ja: string };
    resonance?: { note: string };
  };
  disclaimer?: string;
};

export async function fetchHumanFortune(
  birth: string, targetDate: string,
): Promise<ApiHumanFortune | null> {
  const q = new URLSearchParams({
    entity_type: "human", birth_date: birth, target_date: targetDate,
  });
  try {
    const r = await fetch(`${API_BASE}/v1/day-fortune?${q}`, { cache: "no-store" });
    if (!r.ok) return null;
    return (await r.json()) as ApiHumanFortune;
  } catch {
    return null;
  }
}

// ---------- 月間カレンダー(日別パーソナルデー) ----------
export type ApiCalendarDay = {
  date: string;
  weekday: number; // 0=月 … 6=日 (Python weekday)
  value: number;
  day_theme: string;
};

export type ApiMonthCalendar = {
  year: number;
  month: number;
  personal_year: ApiCycle;
  personal_month: ApiCycle;
  days: ApiCalendarDay[];
};

export async function fetchMonthCalendar(
  birth: string, year: number, month: number,
): Promise<ApiMonthCalendar | null> {
  const q = new URLSearchParams({
    birth_date: birth, year: String(year), month: String(month),
  });
  try {
    const r = await fetch(`${API_BASE}/v1/month-calendar?${q}`, { cache: "no-store" });
    if (!r.ok) return null;
    return (await r.json()) as ApiMonthCalendar;
  } catch {
    return null;
  }
}
