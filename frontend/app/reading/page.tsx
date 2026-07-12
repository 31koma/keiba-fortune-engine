"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import BirthdateModal from "../components/BirthdateModal";
import Orbit from "../components/Orbit";
import { buildQuadReading, QuadPerson } from "@/lib/reading";

function PersonCard({ p }: { p: QuadPerson }) {
  return (
    <div className="quad-card">
      <div className="quad-label">{p.label}</div>
      <div className="quad-name">{p.name}</div>
      <div className="quad-stats">
        <span>{p.label === "レース日" ? `UD ${p.lp}` : `LP ${p.lp}`}</span>
        <span>{p.sign}{p.boundary ? "(境界日)" : ""}</span>
        {p.pd !== null && <span>PD {p.pd}</span>}
      </div>
      {p.theme.word && <div className="quad-theme">「{p.theme.word}」</div>}
      <div className="quad-role">{p.role}</div>
    </div>
  );
}

function ReadingBody() {
  const params = useSearchParams();
  const raceId = params.get("race") ?? "";
  const horseId = params.get("horse") ?? "";
  const [birth, setBirth] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [modal, setModal] = useState(false);
  useEffect(() => { setBirth(localStorage.getItem("birthdate")); setReady(true); }, []);

  if (!ready) return <main />;

  if (!birth) {
    return (
      <main>
        <Link href="/races" className="back">← レース一覧へ戻る</Link>
        <section className="you-invite">
          <div className="theme-label">4者分析</div>
          <p className="races-q">最後の一者は、あなたです。</p>
          <p className="races-sub">
            馬・騎手・レース日は揃いました。あなたの生年月日を加えると、
            4つの軌道が交わる「あなただけの読み」になります。
          </p>
          <button className="cta" onClick={() => setModal(true)}>生年月日を登録する</button>
        </section>
        {modal && <BirthdateModal onClose={() => setModal(false)}
          onSaved={(v) => { setBirth(v); setModal(false); }} />}
      </main>
    );
  }

  const r = buildQuadReading(raceId, horseId, birth);
  if (!r) {
    return (
      <main>
        <Link href="/races" className="back">← レース一覧へ戻る</Link>
        <p className="races-sub" style={{ marginTop: 30 }}>対象が見つかりませんでした(Mockデータ外)。</p>
      </main>
    );
  }

  const otherHorse = r.race.entries.find((e) => e.horseId !== horseId);

  return (
    <main>
      <Link href="/races" className="back">← レース一覧へ戻る</Link>

      <section className="reading-head">
        <div className="race-meta">
          {r.race.date}・{r.race.course} {r.race.number}R・{r.race.name}
        </div>
        <h1 className="reading-title">
          {r.entry.post}番 {r.horse.name}
          <span> 鞍上 {r.jockey.name}</span>
        </h1>
      </section>

      <section className={`sync-box sync-${r.sync.tier}`}>
        <div className="sync-label">今日のシンクロ度</div>
        <div className="sync-stars" aria-hidden="true">
          {"★".repeat(r.sync.stars)}{"☆".repeat(10 - r.sync.stars)}
        </div>
        <div className="sync-score">
          {r.sync.score.toFixed(1)}<span className="sync-max"> / 10</span>
        </div>
        <div className="sync-word">{r.sync.label}</div>
        <p className="sync-note">
          4者(馬・騎手・レース日・あなた)の占術的な調和度です。
          レース結果や勝率ではありません。※開発用の暫定値(Mock)
        </p>
      </section>

      <section className="you-sec today" style={{ marginTop: 24 }}>
        <div className="theme-label">今回の結論</div>
        <p className="conclusion">「{r.conclusion.title}」</p>
        <p className="theme-line" style={{ textAlign: "left" }}>{r.conclusion.body}</p>
        <p className="stars-note">{r.band}(帯は開発用の暫定表示です)</p>
      </section>

      <section className="you-sec blueprint">
        <h2>今回の共通テーマ</h2>
        <div className="theme-word" style={{ marginTop: 16 }}>{r.common_theme.word}</div>
        <p className="theme-line">{r.common_theme.line}</p>
        <div className="orbit-wrap" style={{ width: "min(240px, 70vw)", margin: "18px auto 0" }}>
          <Orbit userActive={true} />
        </div>
      </section>

      <div className="quad-grid">
        <PersonCard p={r.horse} />
        <PersonCard p={r.jockey} />
        <PersonCard p={r.race_day} />
        <PersonCard p={r.user} />
      </div>

      <section className="you-sec"><h2>噛み合っているところ</h2><p>{r.aligned_points}</p></section>
      <section className="you-sec"><h2>流れが動きやすいところ</h2><p>{r.moving_points}</p></section>
      <section className="you-sec"><h2>慎重に見たいところ</h2><p>{r.caution_points}</p></section>
      <section className="you-sec"><h2>あなたにとっての注目点</h2><p>{r.user_focus}</p></section>

      <section className="you-sec today">
        <div className="theme-label">{r.final_viewpoint.label}</div>
        <p className="conclusion" style={{ fontSize: 17 }}>「{r.final_viewpoint.line}」</p>
      </section>

      <details className="dev-details">
        <summary>開発情報(使用ルール・ステータス)</summary>
        <ul>
          {r.used_rules.map((u) => <li key={u}>{u}</li>)}
          <li>hypothesis_status: {r.hypothesis_status}</li>
          <li>validation_status: {r.validation_status}</li>
        </ul>
      </details>

      <section className="you-next">
        {otherHorse && (
          <Link href={`/reading?race=${r.race.id}&horse=${otherHorse.horseId}`}
            className="cta-sub" style={{ display: "block", textDecoration: "none" }}>
            別の馬を見る({otherHorse.horseName})
          </Link>
        )}
        <div className="home-links">
          <Link href="/races">今日のレース一覧へ</Link>
          <Link href="/you">あなたの基本設計図</Link>
          <Link href="/compat">相性をみる</Link>
        </div>
      </section>

      <footer>
        ※{r.disclaimer}
        <br />開発版: 本画面の分析はMockデータです(正式実装では知識ベース+POST /v1/readings/horse-triad から生成します)。
      </footer>
    </main>
  );
}

export default function Reading() {
  return (
    <Suspense fallback={<main />}>
      <ReadingBody />
    </Suspense>
  );
}
