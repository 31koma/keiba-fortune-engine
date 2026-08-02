"use client";
// 「星読みターフの見方」— 初めての人が30秒で世界観をつかむための説明カード。
// 初回訪問時は開いた状態、以降は開閉状態をlocalStorageに記憶する。
// ✦の説明は現在の実装仕様(この日のおすすめ/隠れ推しレース/レース内の収束トップ)に準拠。
import { useEffect, useState } from "react";

const KEY = "guide_open";

const METRICS: [string, string, string][] = [
  ["主", "総合", "あなた・市場・馬・騎手・レース日を含めた総合評価です。"],
  ["客", "客観", "あなたを除き、市場・馬・騎手・レース日から見る客観評価です。"],
  ["本", "本質", "馬・騎手・レース日の調和だけを見る本質評価です。"],
  ["数", "数理", "戦績の流れや波形から読み解く数理評価です。"],
  ["収", "収束", "星と戦績が同じ方向を向いたときの最終評価です。"],
];

const STARS: [string, string][] = [
  ["この日のおすすめ", "その日の全出走の中で、収束がもっとも強い組み合わせに付きます(走歴が浅く確信度の低い馬は看板にしません)。"],
  ["レース一覧の ✦", "「隠れ推し」がいるレースの印です。集合意識の注目はまだ薄いのに、収束の強い馬がいることを示します。"],
  ["出走表の ✦", "そのレースで収束度がいちばん高い馬に付きます。"],
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

          <div className="guide-sec-title">5つの指標</div>
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
            左から順に要素を削ぎ落とし、最後に「収」で結論へ収束する流れです。
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
