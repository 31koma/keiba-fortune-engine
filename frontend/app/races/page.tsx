"use client";
import Link from "next/link";
import { useState } from "react";
import { MOCK_RACES } from "@/lib/mock";
import { dayTheme, lifePath, sunSign } from "@/lib/preview";

export default function Races() {
  const [openBoundary, setOpenBoundary] = useState<string | null>(null);

  return (
    <main>
      <Link href="/" className="back">← 入口へ戻る</Link>

      <section className="races-lead">
        <p className="races-q">今日、最初に気になった一頭は<br />どの馬ですか?</p>
        <p className="races-sub">
          占術は、その「気になる」という直感も大切にします。
        </p>
      </section>

      {MOCK_RACES.map((race) => (
        <section key={race.id}>
          <div className="race-head">
            <span className="race-title">{race.name}</span>
            <span className="race-meta">{race.date}・{race.course} {race.number}R・{race.distance}</span>
          </div>

          {race.entries.map((e, i) => {
            const theme = dayTheme(e.horseBirth, race.date);
            const sign = sunSign(e.horseBirth);
            const featured = race.featuredHorseId === e.horseId;
            return (
              <article className={`horse-card ${featured ? "featured" : ""}`}
                key={e.horseId} style={{ animationDelay: `${i * 90}ms` }}>
                {featured && (
                  <div className="featured-tag">
                    ✦ 今日の注目
                    <span>占術上、今日の流れが強い一頭 — 予想ではありません</span>
                  </div>
                )}

                <header className="horse-head">
                  <div>
                    <div className="horse-name">{e.horseName}</div>
                    <div className="horse-sub">{e.post}番・鞍上 {e.jockeyName}</div>
                  </div>
                </header>

                <div className="theme-hero">
                  <div className="theme-label">今日のテーマ</div>
                  <div className="theme-word">{theme.word}</div>
                  <p className="theme-line">{theme.line}</p>
                </div>

                <div className="ministats">
                  <div className="stat">
                    <div className="stat-num">{lifePath(e.horseBirth)}</div>
                    <div className="stat-key">ライフパス</div>
                  </div>
                  <div className="stat">
                    <div className="stat-num stat-sign">{sign.ja}</div>
                    <div className="stat-key">
                      太陽星座
                      {sign.boundary && (
                        <button className="boundary-q" aria-label="境界日とは"
                          onClick={() => setOpenBoundary(openBoundary === e.horseId ? null : e.horseId)}>
                          境界日?
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                {openBoundary === e.horseId && (
                  <p className="boundary-note">
                    星座が切り替わる特別な日に生まれています。厳密な判定は天文暦で行うため、
                    両方の星座の気質を持つ可能性がある日です。
                  </p>
                )}

                <button className="quad-btn"
                  onClick={() =>
                    alert("4者分析(馬×騎手×今日×あなた)の画面は次のフェーズで実装します。\n物語と「今回の結論」をここで提示予定です。")
                  }>
                  この馬とあなたの物語を読む
                </button>
                <p className="quad-cap">馬 × 騎手 × 今日 × あなた — 4者分析</p>
              </article>
            );
          })}
        </section>
      ))}

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果を予測・保証するものではありません。
        <br />
        開発版: テーマ・注目はMockデータです(正式実装では知識ベースが決定します)。
      </footer>
    </main>
  );
}
