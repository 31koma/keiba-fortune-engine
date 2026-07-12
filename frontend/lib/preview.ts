// 開発用プレビュー計算(フロント暫定)。
// 正式にはバックエンド /v1/profile(知識ベース駆動)へ置換する。
// ここの一言文言はMock(正本非由来)であり、鑑定本文には使用しない。

export function lifePath(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const digits = (n: number) =>
    String(n).split("").reduce((a, c) => a + Number(c), 0);
  const reduce = (n: number): number => {
    while (n > 9 && ![11, 22, 33].includes(n)) n = digits(n);
    return n;
  };
  return reduce(reduce(m) + reduce(d) + reduce(digits(y)));
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
  const [ja, en, s, e] = hit ?? SIGNS[0];
  const near = SIGNS.some(([, , bs, be]) =>
    [bs, be].some((b) => Math.abs(Number(md.replace("-", "")) - Number(b.replace("-", ""))) <= 1));
  return { ja, en, boundary: near };
}

// Mock一言(開発用。正式版は知識ベースのテンプレートから生成)
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
