"use client";
// 「星読みターフの見方」— 初めての人が30秒で世界観をつかむための説明カード。
// 初回訪問時は開いた状態、以降は開閉状態をlocalStorageに記憶する。
// ✦の説明は現在の実装仕様に準拠すること。
// 2026-08-16時点: この日のおすすめ=合トップ(conf low のみ除外) /
// レース一覧=隠れ推しレース / 出走表=レース内の合トップ(同じく conf low のみ除外)。
// ※ 2026-08-15に入れた「騎↓調↓セルを除外」は run12 のP8判定で撤去した。
// **fifty.ts の topByFifty を変えたら、必ずここの文言も直す。**
import { useEffect, useState } from "react";

const KEY = "guide_open";

// 検証(run1〜12)にもとづく実践ルール。むずかしい理屈ぬきで「こう見れば良い」だけを書く。
const RULES: [string, string][] = [
  ["まずは「合」を見る", "合=スピ(収)50%×物理(理・騎・調)50%の総合点。おすすめ・✦・レース一覧の数字はぜんぶこの点で選ばれています。迷ったら合がいちばん濃い馬。"],
  ["くわしく見たい時は4つの色", "収・理・騎・調。数字は読まなくていい。色は 赤→橙→青→緑→金 の順に良くなります。"],
  ["1〜3番人気の馬は「騎」と「調」だけ見る", "人気馬どうしは収・理でくらべても差が出ません。でも鞍上と仕上がりはここでこそ効きます。騎・調が両方濃い人気馬は複勝62%、両方薄いと40%(11開催日・1180頭)。"],
  ["4番人気より下は、濃い色の数を数える", "収・理・騎・調のうち「青より濃い色」が多い馬ほど走りやすい。ぜんぶ薄い馬は消していい。"],
  ["ねらい目は「収」と「理」が両方濃い馬", "星と実力が重なった馬。同じ人気の馬たちより頭ひとつ走っています。"],
  ["収だけ金ピカで他が薄い馬は「応援枠」", "今日いちばんドラマを持っている馬。心で応援、財布は別。"],
  ["✦や★の多いレースが今日の主役レース", "観るならそこ。今日いちばん熱い物語が待っています。"],
];

const METRICS: [string, string, string][] = [
  ["合", "50/50", "スピ(収)50%×物理(理・騎・調)50%。おすすめと✦はこの点で選ばれます。"],
  ["主", "総合", "あなた・市場・馬・騎手・レース日を含めた総合評価です。"],
  ["客", "客観", "あなたを除き、市場・馬・騎手・レース日から見る客観評価です。"],
  ["本", "本質", "馬・騎手・レース日の調和だけを見る本質評価です。"],
  ["数", "数理", "戦績の流れや波形から読み解く数理評価です。"],
  ["収", "収束", "星と戦績が同じ方向を向いたときの最終評価です。高い「グループ」が走りやすい数字で、1頭を当てる数字ではありません。"],
  ["理", "能力", "馬の実力(JRDB IDM)。10点満点(本日の最高=10)。"],
  ["調", "仕上がり", "調教の良さ。10点満点。"],
  ["騎", "騎手", "鞍上の腕。10点満点。"],
];

const STARS: [string, string][] = [
  ["この日のおすすめ", "その日の全出走の中で「合」がいちばん高い馬に付きます。走歴が浅く確信度の低い馬だけは看板にしません。"],
  ["レース一覧の ✦", "「隠れ推し」がいるレースの印です。集合意識の注目はまだ薄いのに、収束の強い馬がいることを示します。"],
  ["出走表の ✦", "そのレースで「合」がいちばん高い馬に付きます。"],
];

export default function GuideCard() {
  const [open, setOpen] = useState(true);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const saved = localStorage.getItem(KEY);
    if (saved !== null) setOpen(saved === "1");  // 未保存(初回)は開いたまま
    setReady(true);
  }, []);
  const toggle = () => {
    const next = !open;
    setOpen(next);
    localStorage.setItem(KEY, next ? "1" : "0");
  };

  return (
    <section className={`guide-card ${ready && open ? "guide-opened" : ""}`}>
      <button className="guide-head" onClick={toggle}
        aria-expanded={open} aria-controls="guide-body">
        <span className="guide-title">
          <span className="guide-star">✦</span> 星読みターフの見方
        </span>
        <span className={`guide-chev ${open ? "up" : ""}`} aria-hidden>⌄</span>
      </button>
      <div className="guide-body-wrap" id="guide-body">
        <div className="guide-body">
          <p className="guide-lede">
            星読みターフは、占術・戦績・流れを組み合わせて競走馬を分析するアプリです。
            「どの馬が強いか」ではなく、<em>「今日はどの馬と流れが重なるか」</em>
            を読み解くことを目的としています。
          </p>

          <div className="guide-sec-title">アプリの見方(決定版) — 7つのルール</div>
          <p className="guide-text" style={{ fontWeight: 700 }}>
            まず「合」。あとは濃い色を数えろ。人気馬は騎と調だけ見る。収+理がそろったら本命級。
          </p>
          <div className="guide-stars">
            {RULES.map(([name, desc], i) => (
              <p className="guide-star-row" key={name}>
                <b>{i + 1}. {name}</b> — {desc}
              </p>
            ))}
          </div>
          <p className="guide-note">
            このルールは実際のレース結果との照合(検証run1〜12)にもとづいています。
          </p>

          <div className="guide-sec-title">9つの指標</div>
          <div className="guide-metrics">
            {METRICS.map(([k, name, desc]) => (
              <div className="guide-metric" key={k}>
                <span className="guide-chip">{k}</span>
                <span className="guide-metric-text">
                  <b>{name}</b> — {desc}
                </span>
              </div>
            ))}
          </div>
          <p className="guide-note">
            主〜収は占術の流れ(要素を削ぎ落とし「収」へ収束)、理・調・騎は物理の実測。
            「合」はその両方を半分ずつ重ねた最終の一点です。
          </p>

          <div className="guide-sec-title">✦ 星マークについて</div>
          <div className="guide-stars">
            {STARS.map(([name, desc]) => (
              <p className="guide-star-row" key={name}>
                <b>{name}</b> — {desc}
              </p>
            ))}
          </div>

          <div className="guide-sec-title">あなたの誕生日</div>
          <p className="guide-text">
            誕生日を登録すると、あなたとの相性を含めた鑑定になります。
            設定で「誕生日を使用しない」を選ぶと、あなたの要素を除いた
            客観的な鑑定へ切り替えられます。
          </p>

          <div className="guide-sec-title">ご利用にあたって</div>
          <p className="guide-text">
            星読みターフは独自理論を研究・検証しながら進化しているアプリです。
            検証で有効性が確認された理論だけを採用し、継続的に改善しています。
          </p>
        </div>
      </div>
    </section>
  );
}
