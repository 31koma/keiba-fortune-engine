// 4者分析(馬×騎手×レース日×あなた)のMock生成(開発版)。
// 正式実装ではバックエンド POST /v1/readings/horse-triad(知識ベース駆動)+
// 利用者軸の拡張APIへ置換する。文言・役割・バンド判定は全て暫定Mockであり、
// 正式な統合スコア・重みは正本側で未定義(validation_required)。
import { MOCK_RACES, MockRace, MockEntry } from "./mock";
import { dayTheme, lifePath, personalDay, sunSign } from "./preview";

const digits = (n: number) => String(n).split("").reduce((a, c) => a + +c, 0);
const reduce = (n: number) => { while (n > 9 && ![11, 22, 33].includes(n)) n = digits(n); return n; };
export const universalDay = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return reduce(digits(y) + digits(m) + digits(d));
};

const GROUPS: Record<string, number[]> = {
  independent: [1, 5, 7], practical: [2, 4, 8], harmonious: [3, 6, 9],
};
const baseN = (n: number) => { while (n > 9) n = digits(n); return n; };
const groupOf = (n: number) => Object.keys(GROUPS).find((g) => GROUPS[g].includes(baseN(n)))!;

const ROLES: Record<string, string> = {
  independent: "流れを動かす役割",
  practical: "流れを整える役割",
  harmonious: "場をつなぐ役割",
};
const DAY_ROLES: Record<string, string> = {
  independent: "変化を促す背景",
  practical: "土台を固める背景",
  harmonious: "調和を広げる背景",
};

const THEME_LIST = ["挑戦", "調和", "集中", "変化", "再出発", "安定", "直感", "成長", "継続", "転換"];

export type QuadPerson = {
  label: string; name: string; lp: number; sign: string; boundary: boolean;
  pd: number | null; theme: { word: string; line: string }; role: string;
};

export type QuadReading = {
  race: MockRace; entry: MockEntry;
  horse: QuadPerson; jockey: QuadPerson; race_day: QuadPerson; user: QuadPerson;
  conclusion: { title: string; body: string };
  common_theme: { word: string; line: string };
  aligned_points: string; moving_points: string; caution_points: string;
  user_focus: string;
  final_viewpoint: { label: string; line: string };
  band: string;
  used_rules: string[]; hypothesis_status: string; validation_status: string;
  disclaimer: string;
};

export function buildQuadReading(
  raceId: string, horseId: string, userBirth: string,
): QuadReading | null {
  const race = MOCK_RACES.find((r) => r.id === raceId);
  const entry = race?.entries.find((e) => e.horseId === horseId);
  if (!race || !entry) return null;

  const mk = (label: string, name: string, birth: string): QuadPerson => ({
    label, name, lp: lifePath(birth), sign: sunSign(birth).ja,
    boundary: sunSign(birth).boundary,
    pd: personalDay(birth, race.date), theme: dayTheme(birth, race.date),
    role: ROLES[groupOf(personalDay(birth, race.date))],
  });

  const horse = mk("競走馬", entry.horseName, entry.horseBirth);
  const jockey = mk("騎手", entry.jockeyName, entry.jockeyBirth);
  const user = mk("あなた", "あなた", userBirth);
  user.role = "今回の流れを受け取る視点";

  const ud = universalDay(race.date);
  const race_day: QuadPerson = {
    label: "レース日", name: race.date, lp: ud, sign: sunSign(race.date).ja,
    boundary: false, pd: null,
    theme: { word: "", line: "" }, role: DAY_ROLES[groupOf(ud)],
  };
  race_day.theme = { word: THEME_LIST[(ud * 3) % THEME_LIST.length],
    line: "その日全体の空気(全馬・全騎手に共通する背景)です。" };

  // ---- 関係の集計(Mock。正式は知識ベースの合成規則で決定) ----
  const groups = [horse, jockey, user].map((p) => groupOf(p.pd ?? p.lp));
  const udGroup = groupOf(ud);
  const overlap = groups.filter((g) => g === groupOf(horse.pd!)).length
    + (udGroup === groupOf(horse.pd!) ? 1 : 0);
  const userAligned = groupOf(user.pd!) === groupOf(horse.pd!)
    || user.pd === horse.pd;

  const commonWord = THEME_LIST[(horse.pd! + jockey.pd! + user.pd! + ud) % THEME_LIST.length];

  const band = overlap >= 3
    ? "占術上の追い風がある組み合わせ"
    : overlap === 2
      ? "展開との相性を確認したい組み合わせ"
      : "慎重に評価したい組み合わせ";

  return {
    race, entry, horse, jockey, race_day, user,
    conclusion: {
      title: overlap >= 3
        ? "同じ方向を向きやすい組み合わせ"
        : overlap === 2
          ? "噛み合えば流れが生まれる組み合わせ"
          : "違いの多さが見どころの組み合わせ",
      body: `馬の「${horse.theme.word}」とレース日の空気が${overlap >= 2 ? "重なりやすく" : "異なるリズムを刻み"}、`
        + `騎手の「${jockey.theme.word}」がその流れを${groupOf(jockey.pd!) === "practical" ? "支えています" : "動かしています"}。`
        + (userAligned
          ? "あなた自身の日運とも共通する要素があり、占術上は注目して見ておきたい組み合わせです。"
          : "あなたの日運は別のリズムにあり、一歩引いた視点で全体を眺めやすい日です。"),
    },
    common_theme: {
      word: commonWord,
      line: `4者のうち複数に、「${commonWord}」へ向かう要素が重なっています。`,
    },
    aligned_points: userAligned
      ? `あなたと馬のパーソナルデイが同じ系統にあり、馬の「${horse.theme.word}」がそのまま響きやすい配置です。騎手の${jockey.role.replace("役割", "力")}も、同じ物語の中で働きます。`
      : `馬と騎手のテーマが「${horse.theme.word}」と「${jockey.theme.word}」として並び、互いの持ち場が分かれている配置です。役割の分担が今日の噛み合わせどころです。`,
    moving_points: `レース日のユニバーサルデイは${ud}(${race_day.theme.word}の空気)。この背景の上で、馬の「${horse.theme.word}」が最も動きを生みやすい要素です。`,
    caution_points: overlap >= 3
      ? "似た要素が重なるぶん、同じ方向に強調されすぎる可能性があります。流れが向かない展開になった時の切り替えに注目です。"
      : "4者のテンポが揃っているわけではありません。悪い配置ではなく、どの要素が主導権を取るかで景色が変わる組み合わせです。",
    user_focus: userAligned
      ? `今日のあなたは「${user.theme.word}」の日。この馬の勢いと同じ方向を向いているので、普段より素直に見どころが目に入りそうです。`
      : `今日のあなたは「${user.theme.word}」の日。この馬とはリズムが違うぶん、普段なら見過ごす細部に目が向きやすい日です。`,
    final_viewpoint: {
      label: userAligned ? "今日、この馬を見る理由" : "今回の見方",
      line: userAligned
        ? "あなたと馬の流れが、同じ方向を向いているから。"
        : `勢いだけでなく、騎手の「${jockey.theme.word}」がどう効くかに注目したい組み合わせです。`,
    },
    band,
    used_rules: [
      "numerology.life_path / personal_day / universal_day(正本式・preview実装)",
      "zodiac.sun_sign(tropical・境界±1日)",
      "group法・役割づけ(Mock: 正式は知識ベース合成規則step0-5)",
    ],
    hypothesis_status: "app_hypothesis",
    validation_status: "validation_required(統合スコアは正本側で未定義)",
    disclaimer: "本鑑定は占術に基づくエンターテインメントであり、レース結果や馬券の的中を予測・保証するものではありません。",
  };
}
