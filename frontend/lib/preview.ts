// 開発用プレビュー計算(フロント暫定)。
// 正式にはバックエンドAPI(知識ベース駆動)へ置換する。
// テーマ語・一言文言はMock(正本非由来)であり、鑑定本文には使用しない。

const digits = (n: number) => String(n).split("").reduce((a, c) => a + Number(c), 0);
const reduce = (n: number): number => {
  while (n > 9 && ![11, 22, 33].includes(n)) n = digits(n);
  return n;
};

export function lifePath(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return reduce(reduce(m) + reduce(d) + reduce(digits(y)));
}

/** パーソナルデイ(馬×対象日)。式は正本numerology_coreの定義に準拠 */
export function personalDay(birthIso: string, targetIso: string): number {
  const [, bm, bd] = birthIso.split("-").map(Number);
  const [ty, tm, td] = targetIso.split("-").map(Number);
  const py = reduce(reduce(bm) + reduce(bd) + reduce(digits(ty)));
  const pm = reduce(py + tm);
  return reduce(pm + reduce(td));
}

const SIGNS: [string, string, string, string][] = [
  ["牡羊座", "Aries", "03-21", "04-19"], ["牡牛座", "Taurus", "04-20", "05-20"],
  ["双子座", "Gemini", "05-21", "06-21"], ["蟹座", "Cancer", "06-22", "07-22"],
  ["獅子座", "Leo", "07-23", "08-22"], ["乙女座", "Virgo", "08-23", "09-22"],
  ["天秤座", "Libra", "09-23", "10-23"], ["蠍座", "Scorpio", "10-24", "11-22"],
  ["射手座", "Sagittarius", "11-23", "12-21"], ["山羊座", "Capricorn", "12-22", "01-19"],
  ["水瓶座", "Aquarius", "01-20", "02-18"], ["魚座", "Pisces", "02-19", "03-20"],
];

export function sunSign(iso: string): { ja: string; en: string; boundary: boolean } {
  const md = iso.slice(5);
  const hit = SIGNS.find(([, , s, e]) => (s <= e ? md >= s && md <= e : md >= s || md <= e));
  const [ja, en] = hit ?? SIGNS[0];
  const near = SIGNS.some(([, , bs, be]) =>
    [bs, be].some((b) => Math.abs(Number(md.replace("-", "")) - Number(b.replace("-", ""))) <= 1));
  return { ja, en, boundary: near };
}

// ---- Mock一言(開発用。正式版は知識ベースから生成) ----
const LINES: Record<number, string> = {
  1: "先頭を切って動き出すタイプです。",
  2: "調和と気配りに強みがあるタイプです。",
  3: "表現力と明るさで場を動かすタイプです。",
  4: "積み重ねで信頼を築くタイプです。",
  5: "変化を楽しみ、機を見るのが速いタイプです。",
  6: "周囲を支える調和のタイプです。",
  7: "探究心と直感をあわせ持つタイプです。",
  8: "勝負所で力を発揮するタイプです。",
  9: "全体を見渡し、締めくくるタイプです。",
  11: "鋭い直感がひらめくタイプです。",
  22: "大きな構想を形にするタイプです。",
  33: "深い共感で人を動かすタイプです。",
};
export const previewLine = (lp: number) => LINES[lp] ?? "";

// ---- 今日のテーマ(パーソナルデイ由来・Mock文言) ----
export const DAY_THEMES: Record<number, { word: string; line: string }> = {
  1: { word: "再出発", line: "今日は新しい流れが立ち上がりやすい日。最初の一歩が鍵になりそうです。" },
  2: { word: "調和", line: "今日は呼吸を合わせる力が活きやすい日。折り合いに注目したいところです。" },
  3: { word: "表現", line: "今日は持ち味が外に出やすい日。のびのびした動きに注目です。" },
  4: { word: "継続", line: "今日は地道さが流れを支える日。淡々としたリズムが強みになりそうです。" },
  5: { word: "変化", line: "今日は展開の変わり目に強い日。動きの切り替えが見どころです。" },
  6: { word: "貢献", line: "今日は周囲と噛み合いやすい日。チームの呼吸に注目したいところです。" },
  7: { word: "集中", line: "今日は内に力を溜めやすい日。静かな集中が流れを作りそうです。" },
  8: { word: "勝負", line: "今日は勝負所で力が出やすい日。直感より行動が鍵になりそうです。" },
  9: { word: "完了", line: "今日はひと区切りの流れの日。仕上がりの良さに注目です。" },
  11: { word: "直感", line: "今日はひらめきが冴えやすい日。流れを掴む一瞬に注目です。" },
  22: { word: "飛躍", line: "今日は大きな流れに乗りやすい日。スケールの大きさが見どころです。" },
  33: { word: "共感", line: "今日は場の空気と深く共鳴しやすい日。一体感に注目です。" },
};
export const dayTheme = (birthIso: string, targetIso: string) =>
  DAY_THEMES[personalDay(birthIso, targetIso)] ?? { word: "—", line: "" };
