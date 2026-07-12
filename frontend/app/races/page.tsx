"use client";
import Link from "next/link";
import { MOCK_RACES } from "@/lib/mock";

export default function Races() {
  return (
    <main>
      <Link href="/" className="back">← 入口へ戻る</Link>
      <section className="hero" style={{ paddingTop: 8, textAlign: "left" }}>
        <h1 className="brand" style={{ fontSize: 22 }}>今日のレース</h1>
        <p className="lede">気になる一頭から、物語を始めましょう。(開発版: Mockデータ)</p>
      </section>

      {MOCK_RACES.map((race) => (
        <article className="race-card" key={race.id}>
          <div className="race-meta">
            {race.date}・{race.course} {race.number}R・{race.distance}
          </div>
          <div className="race-name">{race.name}</div>
          {race.entries.map((e) => (
            <div className="entry" key={e.horseId}>
              <span className="post">{e.post}</span>
              <span className="names">
                <span className="horse">{e.horseName}</span>
                <br />
                <span className="jockey">
                  {e.jockeyName} / 馬の生まれ日 {e.horseBirth}
                </span>
              </span>
              <button
                onClick={() =>
                  alert("この馬の鑑定画面は次のフェーズで実装します。\n(数秘×星座×パーソナルデイの物語と「今回の結論」をここで提示予定)")
                }
              >
                鑑定へ
              </button>
            </div>
          ))}
        </article>
      ))}

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果を予測・保証するものではありません。
      </footer>
    </main>
  );
}
