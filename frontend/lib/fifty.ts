// 「合」= 50/50総合。スピ(収)50% × 物理(理・調・騎の平均)50%。
// 検証run10(10開催日バックテスト: 騎+17.8/+11.2/+9.0pt・調+16.3/+10.6/+10.0pt、
// 帯内中央値分割)にもとづく「選定用」スコア。占術スコア(収)そのものには混ぜない。
// おすすめ・✦・レース一覧の数字はこの点で選ぶ(2026-08-09 オーナー決定)。
//
// ── p表v4フィルタの経緯(入れて、外した) ────────────────────────────
// 2026-08-15: run11で事前登録P1(騎手指数)・P2(調教指数)が再現したため、
//   看板(おすすめ・✦)から最悪セル「騎↓調↓」を除外するフィルタを入れた。
//   「騎↑調↑必須」は8/15の実測で36レース中11レースが入れ替わり複52.8%→47.2%と
//   悪化したため採らず、除外だけにした。
// 2026-08-16: **prereg_run12のP8で不支持となり、決定ルールに従ってフィルタを外した。**
//   フィルタあり複50.0% 対 なし52.8%(レース内合トップ36頭)。
//   差-2.8ptの全量は中京1Rの1頭(除外したバクソウシャチョウ 合6.0 low/low が2着、
//   代打のスマートメモリー 合4.5 high/high が4着)で、入れ替わりは36レース中1レースだけ。
//   根拠は薄いが、事前に登録した決定ルールは結果を見てから曲げない。
//   **層としての騎↑調↑(P6は3帯すべてで支持)は本物だが、それは帯の平均の話であり、
//   1点を選ぶ場面では検証済みの合そのものが最も強い。**
//   p表v4(v4_cell / p_v4)は残す — EVの計算と表示には引き続き使う。
//   フィルタを再投入する場合は、少なくとも3開催日ぶんの事前登録を切ってからにすること。
import { ApiRecoItem } from "./api";

export function fiftyOf(it: ApiRecoItem): number | null {
  const oshi = it.oshi?.score ?? null;
  const ph = it.physical;
  const parts = [ph?.idm10, ph?.cyokyo10, ph?.joc10]
    .filter((v): v is number => v != null);
  const phys = parts.length
    ? parts.reduce((a, b) => a + b, 0) / parts.length : null;
  if (oshi == null && phys == null) return null;
  if (oshi == null) return Math.round(phys! * 10) / 10;
  if (phys == null) return Math.round(oshi * 10) / 10;
  return Math.round(((oshi + phys) / 2) * 10) / 10;
}

/** p表v4の最上位セル(騎手指数・調教指数がともに人気帯内で上位半分)か */
export function isV4Top(it: ApiRecoItem): boolean {
  return it.physical?.v4_cell === "high/high";
}

/** p表v4の最下位セル(騎手指数・調教指数がともに人気帯内で下位半分)か。
 *  2026-08-16以降、看板の選定には使っていない(上の経緯を参照)。表示・分析用。 */
export function isV4Bottom(it: ApiRecoItem): boolean {
  return it.physical?.v4_cell === "low/low";
}

/** p表v4による複勝率の推定(帯 × 騎調セル)。未付与ならnull */
export function pV4(it: ApiRecoItem): number | null {
  return it.physical?.p_v4 ?? null;
}

/** 合スコア順の先頭馬(走歴の薄い conf low は看板にしない。全馬lowなら仕方なく先頭) */
export function topByFifty(items: ApiRecoItem[]): ApiRecoItem | null {
  const rank = (arr: ApiRecoItem[]) => arr
    .filter((it) => fiftyOf(it) != null)
    .sort((a, b) =>
      (fiftyOf(b)! - fiftyOf(a)!) ||
      (((b.physical?.joc10 ?? 0) + (b.physical?.cyokyo10 ?? 0)) -
       ((a.physical?.joc10 ?? 0) + (a.physical?.cyokyo10 ?? 0))) ||
      ((a.post_number ?? 0) - (b.post_number ?? 0)));
  // ①走歴あり(conf low を除く) → ②全馬 の順に降りる。
  // セルによる除外は run12(2026-08-16)のP8判定で撤去した。
  const solid = rank(items.filter((it) => it.oshi?.confidence !== "low"));
  if (solid.length) return solid[0];
  const all = rank(items);
  return all.length ? all[0] : null;
}
