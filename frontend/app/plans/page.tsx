"use client";
import Link from "next/link";

// サブスクリプションプラン(構想段階のプレビュー。決済は未実装)。
// 方針は MONETIZATION.md 参照 — 売るのは「的中」ではなく「自分だけの読み」。
const FREE = [
  "今日のおすすめ(1日1組)",
  "レース一覧と基本の占術プロフィール",
  "3者分析(馬×騎手×レース日)",
];
const PREMIUM = [
  "あなたを加えた4者分析 — 無制限",
  "全出走のシンクロ度と「隠れシンクロ」の発見",
  "集合意識(オッズ)×占術の共鳴パターン分析",
  "あなた専用の日運と、レース日との重なり",
  "鑑定履歴の保存(あなたの物語のアーカイブ)",
];

export default function Plans() {
  return (
    <main>
      <Link href="/" className="back">← 入口へ戻る</Link>

      <section className="races-lead">
        <p className="races-q">星読みターフのプラン</p>
        <p className="races-sub">
          私たちが売るのは「的中」ではありません。<br />
          いつものレースが自分だけの物語になる、その体験です。
        </p>
      </section>

      <section className="plan-card">
        <div className="plan-name">フリー</div>
        <div className="plan-price">¥0<span> /月</span></div>
        <ul className="plan-list">
          {FREE.map((f) => <li key={f}>{f}</li>)}
        </ul>
        <div className="plan-cta plan-cta-current">いま使えるプラン</div>
      </section>

      <section className="plan-card plan-premium">
        <div className="plan-badge">✦ おすすめ</div>
        <div className="plan-name">プレミアム</div>
        <div className="plan-price">¥980<span> /月(構想)</span></div>
        <ul className="plan-list">
          {PREMIUM.map((f) => <li key={f}>{f}</li>)}
        </ul>
        <div className="plan-cta">準備中 — 実データ連携とあわせて公開予定</div>
      </section>

      <section className="section">
        <h2>星読みターフの4本柱</h2>
        <div className="terms">
          <span className="term"><b>数秘術</b> — 数字が持つ意味やリズム</span>
          <span className="term"><b>西洋占星術</b> — 黄道十二宮と天体が示す設計図</span>
          <span className="term"><b>宿曜占星術</b> — 縁・相性・タイミング(準備中)</span>
          <span className="term"><b>四柱推命</b> — 宿命・運気の流れ(準備中)</span>
        </div>
      </section>

      <section className="section">
        <h2>納得して使ってもらうために</h2>
        <p>
          すべての鑑定は、使ったルールと出典を開示します。
          シンクロ度の算出規則も公開仕様(synchro_v0)です。
          的中や必勝をうたわないこと——それが、長く楽しんでいただくための私たちの約束です。
        </p>
      </section>

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果を予測・保証するものではありません。
        <br />
        価格・特典は構想段階であり、変更される可能性があります。決済機能は未実装です。
      </footer>
    </main>
  );
}
