// 「相性をみる」用のMock生成(開発版)。
// 正式実装ではバックエンド /v1/compatibility(知識ベース駆動:
// 数字グループ法・星座distance法/element法・補完/衝突部品)へ置換する。
// ここでの区分・文言・星の数はすべて暫定Mockであり、正式な重みではない。
import { lifePath, sunSign } from "./preview";

export const RELATION_TYPES = ["気になる人", "恋人・夫婦", "家族", "友人", "仕事仲間"];

const GROUPS: Record<string, number[]> = {
  independent: [1, 5, 7], practical: [2, 4, 8], harmonious: [3, 6, 9],
};
const ELEMENTS: Record<string, string> = {
  牡羊座: "fire", 獅子座: "fire", 射手座: "fire",
  牡牛座: "earth", 乙女座: "earth", 山羊座: "earth",
  双子座: "air", 天秤座: "air", 水瓶座: "air",
  蟹座: "water", 蠍座: "water", 魚座: "water",
};
const HARMONY: Record<string, string[]> = {
  fire: ["fire", "air"], air: ["air", "fire"],
  earth: ["earth", "water"], water: ["water", "earth"],
};
const ELEM_JA: Record<string, string> = { fire: "火", earth: "地", air: "風", water: "水" };

const base = (n: number) => { while (n > 9) n = String(n).split("").reduce((a, c) => a + +c, 0); return n; };
const groupOf = (n: number) => Object.keys(GROUPS).find((g) => GROUPS[g].includes(base(n)))!;

const THEMES: Record<string, string> = {
  成長: "お互いが持っていない景色を見せ合える関係です。理解が深まるほど、二人の可能性も広がっていきます。",
  調和: "無理をしなくても呼吸が合いやすい関係です。安心感が、お互いの一番良い部分を引き出します。",
  信頼: "時間をかけて積み上がる関係です。約束を重ねるほど、揺るがない土台が育っていきます。",
  挑戦: "一緒にいると新しい一歩を踏み出したくなる関係です。互いが互いの起爆剤になります。",
  変化: "会うたびに発見がある関係です。同じ場所に留まらないことが、二人らしさになります。",
  安定: "日常を心地よく整え合える関係です。特別な言葉がなくても伝わるものが増えていきます。",
  直感: "言葉より先に通じ合う瞬間が多い関係です。「なんとなく分かる」を大切にできます。",
  学び: "考え方の違いが、そのまま学びになる関係です。相手は自分にない答えを持っています。",
};
const THEME_KEYS = Object.keys(THEMES);

export type CompatReading = {
  conclusion: string; stars: number; theme: { word: string; line: string };
  attract: string; common: string; diff: string; hint: string;
  keywords: string[]; oneWord: string;
};

export function compatReading(meIso: string, otherIso: string): CompatReading {
  const mLp = lifePath(meIso), oLp = lifePath(otherIso);
  const mG = groupOf(mLp), oG = groupOf(oLp);
  const mE = ELEMENTS[sunSign(meIso).ja], oE = ELEMENTS[sunSign(otherIso).ja];
  const sameGroup = mG === oG || mLp === oLp;
  const harmonious = HARMONY[mE].includes(oE);

  const stars = 3 + (sameGroup ? 1 : 0) + (harmonious ? 1 : 0); // 暫定Mock(正式な重みではない)

  const conclusion = sameGroup && harmonious
    ? "自然に調和しやすい関係"
    : !sameGroup && harmonious
      ? "互いに刺激を与え合う関係"
      : sameGroup
        ? "時間をかけるほど理解が深まりやすい関係"
        : "違いから学びが生まれる関係";

  const themeWord = THEME_KEYS[(mLp + oLp + Math.abs(mE.length - oE.length)) % THEME_KEYS.length];

  const groupLine = sameGroup
    ? "数字のグループ(価値観の土台)が同じで、大切にしたい方向が重なりやすいふたりです。"
    : "数字のグループ(価値観の土台)が異なり、相手が自分にない視点を持っています。";
  const elemLine = harmonious
    ? `星座の元素は${ELEM_JA[mE]}と${ELEM_JA[oE]}。互いを活かし合う組み合わせで、一緒にいるほど流れが軽くなります。`
    : `星座の元素は${ELEM_JA[mE]}と${ELEM_JA[oE]}。テンポの違う組み合わせで、その違いが関係に厚みを与えます。`;

  return {
    conclusion, stars,
    theme: { word: themeWord, line: THEMES[themeWord] },
    attract: harmonious
      ? `${elemLine} 近くにいるだけで気持ちが通いやすいのが、惹かれやすさの正体です。`
      : `${elemLine} 自分と違うリズムだからこそ目で追ってしまう — それが惹かれやすさの正体です。`,
    common: sameGroup
      ? `${groupLine} 「何を大切にするか」で衝突しにくく、同じ景色に感動できるのが強みです。`
      : `${groupLine} それでも「誠実でいたい」という根の部分は共有しやすいふたりです。`,
    diff: sameGroup
      ? "似ているぶん、ゆずれない場面も同じところで訪れます。悪い相性ではなく、鏡のように自分を映し合う瞬間です。"
      : "判断のテンポと優先順位が異なります。これは欠点ではなく、役割の違い — 理解すると強みに変わるポイントです。",
    hint: harmonious
      ? "結論を急がず、相手の考えを最後まで聞く。それだけで、もともと良い流れがさらに滑らかになります。"
      : "違いを直そうとせず、役割の違いとして見る。ひとりの時間と一緒の時間、両方を大切にしてください。",
    keywords: [themeWord, sameGroup ? "共鳴" : "補完", harmonious ? "調和" : "学び"],
    oneWord: harmonious
      ? "今日の小さな「ありがとう」を言葉にして渡すこと。"
      : "相手のペースを一日だけ真似してみること。",
  };
}
