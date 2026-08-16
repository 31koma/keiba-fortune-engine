"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Orbit from "./components/Orbit";
import BirthdateModal from "./components/BirthdateModal";
import GuideCard from "./components/GuideCard";
import { lifePath, sunSign } from "@/lib/preview";
import { dayRecommendations, SYNC_FRAMING } from "@/lib/synchro";
import { ApiDayRecommendations, fetchDayRecommendations } from "@/lib/api";
import { bandFor } from "@/lib/synchroModes";
import { fiftyOf, topByFifty } from "@/lib/fifty";
import { birthdateEnabled, effectiveBirth, setBirthdateEnabled } from "@/lib/settings";

function TodayRecommendation({ birth }: { birth: string | null }) {
  const [api, setApi] = useState<ApiDayRecommendations | null>(null);
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    fetchDayRecommendations(birth).then((d) => { setApi(d); setChecked(true); });
  }, [birth]);

  // ---- 実データ(バックエンドAPI) ----
  // おすすめ=「合」(スピ50%×物理50%)のトップ。lib/fifty.ts 参照(2026-08-09 オーナー決定)
  const pick = api && api.items.length > 0
    ? (topByFifty(api.items) ?? api.recommendation) : api?.recommendation ?? null;
  if (api && pick) {
    const r = pick;
    const s = r.synchro;
    const o = r.oshi ?? null;
    const f = fiftyOf(r);
    const tier = f != null ? bandFor(f).tier : (o ?? s).tier;
    return (
      <section className={`reco-card sync-${tier}`}>
        <div className="reco-head">
          <span className="reco-tag">✦ {api.target_date} のおすすめ</span>
          <span className="reco-race">
            {r.race_name && r.race_name !== "レース"
              ? `${r.race_name}・${r.racecourse}${r.race_number}R`
              : `${r.racecourse}${r.race_number}R`}
          </span>
        </div>
        <div className="reco-main">
          <div className="reco-horse">
            <div className="reco-name">{r.horse_name}</div>
            <div className="reco-sub">
              {r.post_number}番・鞍上 {r.jockey_name}
              {r.win_odds ? `・単勝${r.win_odds}` : ""}
            </div>
          </div>
          <div className="reco-score">
            <span className="sync-score" style={{ fontSize: 34 }}>
              {(f ?? (o ?? s).score).toFixed(1)}<span className="sync-max" style={{ fontSize: 13 }}> /10</span>
            </span>
            <span className="reco-score-key">{f != null ? "合(スピ50×物理50)" : o ? "収束度" : "シンクロ度"}</span>
          </div>
        </div>
        <div className={`pattern-chip pattern-${s.pattern.type}`}>{s.pattern.label_ja}</div>
        <p className="pattern-line">{o?.reasons[0]?.line ?? s.pattern.line}</p>
        <Link className="reco-btn" href={`/races?race=${r.race_id}&horse=${r.horse_id}`}>
          この馬の詳細を見る(合/主/客/本/数/収/理/調/騎)
        </Link>
        <p className="reco-note">{api.framing}({api.provider_credit.data_provider_credit})</p>
      </section>
    );
  }

  // ---- フォールバック(API不達時: 開発用Mock) ----
  if (!checked) return null;
  const top = dayRecommendations(birth)[0];
  if (!top) return null;
  const { race, entry, synchro } = top;
  return (
    <section className={`reco-card sync-${synchro.tier}`}>
      <div className="reco-head">
        <span className="reco-tag">✦ 今日のおすすめ(Mock)</span>
        <span className="reco-race">{race.name}・{race.number}R</span>
      </div>
      <div className="reco-main">
        <div className="reco-horse">
          <div className="reco-name">{entry.horseName}</div>
          <div className="reco-sub">{entry.post}番・鞍上 {entry.jockeyName}</div>
        </div>
        <div className="reco-score">
          <span className="sync-score" style={{ fontSize: 34 }}>
            {synchro.score.toFixed(1)}<span className="sync-max" style={{ fontSize: 13 }}> /10</span>
          </span>
          <span className="reco-score-key">シンクロ度</span>
        </div>
      </div>
      <div className={`pattern-chip pattern-${synchro.pattern.type}`}>{synchro.pattern.label}</div>
      <p className="pattern-line">{synchro.pattern.line}</p>
      <Link className="reco-btn" href={`/reading?race=${race.id}&horse=${entry.horseId}`}>
        {birth ? "この馬とあなたの物語を読む" : "この馬の物語を読む"}
      </Link>
      <p className="reco-note">{SYNC_FRAMING}</p>
    </section>
  );
}

export default function Home() {
  const [modal, setModal] = useState(false);
  const [birth, setBirth] = useState<string | null>(null);
  const [useBirth, setUseBirth] = useState(true);
  useEffect(() => {
    setBirth(localStorage.getItem("birthdate"));
    setUseBirth(birthdateEnabled());
  }, []);
  const effBirth = effectiveBirth(birth, useBirth);

  return (
    <main>
      <section className="hero">
        <div className="brand-en">Hoshiyomi Turf</div>
        <h1 className="brand">星読みターフ</h1>
        <p className="catch">星と数字で、<em>レースを読む。</em></p>
        <p className="lede">
          その馬の生まれ日。騎手の数字。今日の星回り。そして、あなた。
        </p>
      </section>

      <div className="orbit-wrap">
        <Orbit userActive={!!effBirth} />
      </div>
      <p className="orbit-caption">
        4つの生まれ日が交わる一点に、あなただけのレースの物語が生まれます。
      </p>

      <TodayRecommendation birth={effBirth} />

      <GuideCard />

      <Link href="/races" className="cta">今日のレースを見る</Link>
      <Link href="/past" className="cta-past">
        過去レースを見る
        <span className="cta-past-sub">レース前の評価と確定結果を見比べる</span>
      </Link>
      <button className={`cta-sub ${birth ? "registered" : ""}`} onClick={() => setModal(true)}>
        {birth ? "あなたのプロフィール(変更する)" : "自分の生年月日を登録する"}
      </button>
      {birth ? (
        <>
          <label className="cta-note" style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            gap: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={useBirth}
              onChange={(e) => { setUseBirth(e.target.checked);
                setBirthdateEnabled(e.target.checked); }} />
            あなたの誕生日を鑑定に使用する
          </label>
          {useBirth ? (
            <p className="cta-note you-chip">
              あなた: ライフパス {lifePath(birth)}・{sunSign(birth).ja} — 4者分析の準備完了
            </p>
          ) : (
            <p className="cta-note">
              いまは「あなた」を除いた客観鑑定を表示しています(誕生日はいつでも戻せます)
            </p>
          )}
        </>
      ) : (
        <p className="cta-note">登録すると「あなた」の軌道が加わり、4者分析になります</p>
      )}

      <div className="home-links">
        <Link href="/you">あなたを見る</Link>
        <Link href="/compat">相性をみる</Link>
        <Link href="/plans">プラン</Link>
      </div>

      <section className="section">
        <h2>このアプリができること</h2>
        <p>
          数秘術と西洋占星術——2000年続く「読み」の伝統をレンズに、
          競走馬・騎手・レース日・あなたの4者の関係性を分析します。
          さらにJRDBの実測データ(能力・仕上がり・騎手)を重ね、
          スピ50%×物理50%の「合」で今日の一頭を選びます。
          結果を保証するためではなく、いつもの競馬をもっと深く味わうために。
        </p>
        <div className="terms">
          <span className="term"><b>ライフパス</b>(生まれ持った数)</span>
          <span className="term"><b>トライン</b>(120度・最も調和する角度)</span>
          <span className="term"><b>パーソナルデイ</b>(その馬にとっての今日)</span>
          <span className="term"><b>元素</b>(火・地・風・水の気質)</span>
        </div>
      </section>

      <section className="section">
        <h2>分析だけで終わらせない</h2>
        <div className="answer-box">
          <div className="label">今回の結論</div>
          <p>
            すべての鑑定は、参考にできる「今回の結論」で締めくくります。
            根拠(使ったルールと出典)もあわせて提示。
            そして最後にどう読むかは——あなたの楽しみです。
          </p>
        </div>
      </section>

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果を予測・保証するものではありません。
        <br />
        的中・必勝をうたうサービスではなく、馬券の購入を推奨するものでもありません。
        <br />
        知識ベース v1.3 準拠 / JRDB実データ / 週末ごとの検証(run1〜10)を継続中
      </footer>

      {modal && (
        <BirthdateModal
          onClose={() => setModal(false)}
          onSaved={(d) => { setBirth(d); setModal(false); }}
        />
      )}
    </main>
  );
}
