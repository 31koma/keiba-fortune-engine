"use client";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import HorseDetailSheet from "../components/HorseDetailSheet";
import PageNav from "../components/PageNav";
import { MOCK_RACES } from "@/lib/mock";
import { dayTheme, lifePath, sunSign } from "@/lib/preview";
import { computeSynchro } from "@/lib/synchro";
import {
  ApiDayRecommendations, ApiRecoItem, fetchDayRecommendations,
  groupByRace, WAKU_STYLE, wakuOf,
} from "@/lib/api";
import { bandFor, MODES, recompute } from "@/lib/synchroModes";
import { birthdateEnabled, effectiveBirth } from "@/lib/settings";

/** 一覧の4指標セル */
function Metric({ k, v, tier }: { k: string; v: number | null; tier: string | null }) {
  return (
    <span className="metric">
      <span className="metric-key">{k}</span>
      <span className={`metric-val ${tier ? `sync-inline-${tier}` : "metric-none"}`}>
        {v === null ? "—" : v.toFixed(1)}
      </span>
    </span>
  );
}

function MetricStrip({ it }: { it: ApiRecoItem }) {
  const s = it.synchro;
  const kyak = recompute(s.components, MODES.quad.include);
  const hon = recompute(s.components, MODES.market_compare.include);
  const pn = it.pattern_numerology;
  const pnOk = pn && !pn.insufficient;
  const oshi = it.oshi;
  return (
    <span className="metric-strip">
      <Metric k="主" v={s.score} tier={s.tier} />
      <Metric k="客" v={kyak.score} tier={kyak.tier} />
      <Metric k="本" v={hon.score} tier={hon.tier} />
      <Metric k="数" v={pnOk ? pn.score : null}
        tier={pnOk ? bandFor(pn.score).tier : null} />
      <Metric k="収" v={oshi ? oshi.score : null} tier={oshi ? oshi.tier : null} />
    </span>
  );
}

// ---------- WIN5(各レース3頭・客観シンクロ度順) ----------
// 対象の推定: JRAは原則「後半5レース」(通常3場開催は10R/11R帯、最終Rは対象外)。
// 発走14:50〜15:50の窓にちょうど5レースあればそれを採用。ずれる日は
// 最終レースを除いた発走の遅い5レースにフォールバックし、注意書きを出す。
function pickWin5(groups: ReturnType<typeof groupByRace>) {
  const timed = groups
    .filter((g) => g.items[0]?.start_time)
    .slice()
    .sort((a, b) => (a.items[0].start_time! < b.items[0].start_time! ? -1 : 1));
  const window = timed.filter((g) => {
    const t = g.items[0].start_time!;
    return t >= "14:50" && t <= "15:50";
  });
  if (window.length === 5) return { legs: window, confident: true };
  const lastNo = new Map<string, number>();
  timed.forEach((g) => lastNo.set(g.racecourse,
    Math.max(lastNo.get(g.racecourse) ?? 0, g.race_number)));
  const rest = timed.filter((g) => g.race_number !== lastNo.get(g.racecourse));
  return { legs: rest.slice(-5), confident: false };
}

function Win5Section({ groups, onPick }: {
  groups: ReturnType<typeof groupByRace>;
  onPick: (it: ApiRecoItem) => void;
}) {
  const { legs, confident } = useMemo(() => pickWin5(groups), [groups]);
  if (legs.length < 5) return null;
  return (
    <section className="win5-sec">
      <div className="win5-head">
        <span className="win5-title">✦ WIN5候補 各3頭</span>
        <span className="win5-meta">客観シンクロ度順・3×3×3×3×3=243通り</span>
      </div>
      {legs.map((g, i) => {
        const top3 = g.items
          .slice()
          .sort((a, b) =>
            recompute(b.synchro.components, MODES.quad.include).score -
            recompute(a.synchro.components, MODES.quad.include).score)
          .slice(0, 3);
        return (
          <div className="win5-leg" key={g.race_id}>
            <div className="win5-race">
              <span className="win5-no">{i + 1}</span>
              <span className="win5-rname">
                {g.race_name && g.race_name !== "レース"
                  ? g.race_name : `${g.racecourse}${g.race_number}R`}
              </span>
              <span className="win5-rmeta">
                {g.racecourse}{g.race_number}R・{g.items[0].start_time}
              </span>
            </div>
            <div className="win5-picks">
              {top3.map((it) => {
                const k = recompute(it.synchro.components, MODES.quad.include);
                return (
                  <button className="win5-pick" key={it.horse_id} onClick={() => onPick(it)}>
                    <span className="win5-post">{it.post_number}</span>
                    <span className="win5-hname">{it.horse_name}</span>
                    <span className={`win5-score sync-inline-${k.tier}`}>
                      {k.score.toFixed(1)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
      <p className="ipat-hint">
        {confident
          ? "1レース目の発売締切は発走5分前。対象レースはJRA公式でも確認できます"
          : "⚠ 対象レースは発走時刻からの推定です。JRA公式のWIN5対象レース表で確認してください"}
      </p>
    </section>
  );
}

const FOOTER = (
  <footer>
    本鑑定は占術に基づくエンターテインメントであり、
    レース結果を予測・保証するものではありません。
    <br />
    シンクロ度=占術4者の調和+集合意識(オッズ)の共鳴(synchro_v0・検証前の仮説)。
    馬券購入の推奨ではありません。
  </footer>
);

function Waku({ post, headCount }: { post: number | null; headCount: number }) {
  if (!post) return null;
  const st = WAKU_STYLE[wakuOf(post, headCount)];
  return (
    <span className="waku-box" style={{
      background: st.bg, color: st.fg,
      border: st.border ? `1px solid ${st.border}` : "1px solid transparent",
    }}>{post}</span>
  );
}

// ---------- 実データ: 場 → レース → 馬 ----------
function ApiRaces({ api, hasBirth, userOff, initRace, initHorse }: {
  api: ApiDayRecommendations;
  hasBirth: boolean;
  userOff: boolean;   // 誕生日は登録済みだが設定OFF
  initRace: string | null;
  initHorse: string | null;
}) {
  const groups = useMemo(() => groupByRace(api.items), [api.items]);
  const initItem = useMemo(() =>
    (initRace && initHorse)
      ? api.items.find((it) => it.race_id === initRace && it.horse_id === initHorse) ?? null
      : null,
    [api.items, initRace, initHorse]);

  const [course, setCourse] = useState<string | null>(initItem?.racecourse ?? null);
  const [raceId, setRaceId] = useState<string | null>(initItem?.race_id ?? null);
  const [detail, setDetail] = useState<ApiRecoItem | null>(initItem);

  const courses = useMemo(() => {
    const m = new Map<string, number>();
    groups.forEach((g) => m.set(g.racecourse, (m.get(g.racecourse) ?? 0) + 1));
    return Array.from(m.entries());
  }, [groups]);
  const courseGroups = groups.filter((g) => g.racecourse === course);
  const race = groups.find((g) => g.race_id === raceId) ?? null;

  const sheet = detail && (
    <HorseDetailSheet item={detail} hasBirth={hasBirth} userOff={userOff}
      onClose={() => setDetail(null)} />
  );

  // --- 馬一覧(レース選択済み) ---
  if (race) {
    const topId = race.items[0]?.horse_id; // items はスコア降順
    const byPost = race.items.slice().sort((a, b) => (a.post_number ?? 0) - (b.post_number ?? 0));
    return (
      <>
        <PageNav onBack={() => setRaceId(null)} />
        <div className="race-head" style={{ marginTop: 14 }}>
          <span className="race-title">
            {race.race_name && race.race_name !== "レース" ? race.race_name : `${race.racecourse}${race.race_number}R`}
          </span>
          <span className="race-meta">
            {api.target_date}・{race.racecourse}{race.race_number}R
            {byPost[0]?.start_time ? `・${byPost[0].start_time}発走` : ""}
            ・{byPost[0]?.head_count}頭
          </span>
        </div>
        <p className="ipat-hint">✦=このレースの収束トップ。馬をタップすると詳細(主/客/本/数/収)が開きます</p>
        {byPost.map((it) => {
          const featured = it.horse_id === topId;
          return (
            <button key={it.horse_id} className={`ipat-horse ih-col ${featured ? "featured" : ""}`}
              onClick={() => setDetail(it)}>
              <span className="ih-top">
                <Waku post={it.post_number} headCount={it.head_count} />
                <span className="ih-main">
                  <span className="ih-name">
                    {featured && <span className="ih-star">✦ </span>}{it.horse_name}
                  </span>
                  <span className="ih-sub">{it.jockey_name}</span>
                </span>
                <span className="ih-odds">{it.win_odds ? `単${it.win_odds}` : ""}</span>
              </span>
              <MetricStrip it={it} />
            </button>
          );
        })}
        <p className="ipat-hint">
          主=あなたを含めた総合評価 / 客=あなたを除いた客観評価 /
          本=馬・騎手・レース日の本質評価 / 数=戦績の流れと波形を読む数理評価 /
          収=星と戦績が同じ方向を向いたときの最終評価(収束・オッズ不使用)
        </p>
        {FOOTER}
        {sheet}
      </>
    );
  }

  // --- レース一覧(場選択済み) ---
  if (course) {
    return (
      <>
        <PageNav onBack={() => setCourse(null)} />
        <div className="race-head" style={{ marginTop: 14 }}>
          <span className="race-title">{course}</span>
          <span className="race-meta">{api.target_date}・{courseGroups.length}レース</span>
        </div>
        {courseGroups.map((g) => {
          const top = g.items[0];
          const best = top?.oshi ?? null;
          const hasHidden = g.items.some((it) => it.oshi?.hidden);
          return (
            <button key={g.race_id} className="ipat-race" onClick={() => setRaceId(g.race_id)}>
              <span className="ir-no">{g.race_number}R</span>
              <span className="ir-name">
                {hasHidden && <span className="ih-star">✦ </span>}
                {g.race_name && g.race_name !== "レース" ? g.race_name : ""}
              </span>
              <span className="ir-right">
                {best
                  ? <span className={`ih-sync sync-inline-${best.tier}`}>{best.score.toFixed(1)}</span>
                  : top && <span className={`ih-sync sync-inline-${top.synchro.tier}`}>{top.synchro.score.toFixed(1)}</span>}
                <span className="ir-time">{top?.start_time ?? ""}</span>
              </span>
            </button>
          );
        })}
        <p className="ipat-hint">右の数字は各レースの最高収束度(✦=隠れ推しがいるレース)</p>
        {FOOTER}
        {sheet}
      </>
    );
  }

  // --- 場一覧 ---
  return (
    <>
      <PageNav />
      <section className="races-lead">
        <p className="races-q">{api.target_date} の開催</p>
        <p className="races-sub">
          {groups.length}レース・{api.items.length}頭を読みました。
          {api.user_included
            ? "あなたの日運も織り込み済みです。"
            : userOff
              ? "設定により、あなたを除いた客観鑑定を表示しています。"
              : "生年月日を登録すると、あなたを加えた値になります。"}
        </p>
      </section>
      {api.recommendation && (
        <button className="ipat-reco" onClick={() => {
          setCourse(api.recommendation!.racecourse);
          setRaceId(api.recommendation!.race_id);
          setDetail(api.recommendation);
        }}>
          ✦ この日のおすすめ: {api.recommendation.racecourse}{api.recommendation.race_number}R
          {" "}{api.recommendation.horse_name}
          <span className={`ih-sync sync-inline-${(api.recommendation.oshi ?? api.recommendation.synchro).tier}`}>
            {(api.recommendation.oshi ?? api.recommendation.synchro).score.toFixed(1)}
          </span>
        </button>
      )}
      {courses.map(([name, count]) => (
        <button key={name} className="ipat-course" onClick={() => setCourse(name)}>
          <span>{name}</span>
          <span className="ic-meta">{count}レース ›</span>
        </button>
      ))}
      <Win5Section groups={groups} onPick={(it) => {
        setCourse(it.racecourse);
        setRaceId(it.race_id);
        setDetail(it);
      }} />
      {FOOTER}
      {sheet}
    </>
  );
}

// ---------- 開発用Mock(API不達時のみ) ----------
function MockRaces({ birth }: { birth: string | null }) {
  return (
    <>
      <PageNav />
      <section className="races-lead">
        <p className="races-q">開発用Mock表示</p>
        <p className="races-sub">
          バックエンドAPIに接続できないため、架空データを表示しています。
          「星読みターフを起動.command」でサーバーを起動してください。
        </p>
      </section>
      {MOCK_RACES.map((race) => {
        const syncs = new Map(race.entries.map((e) => [e.horseId, computeSynchro(e, race, birth)]));
        return (
          <section key={race.id}>
            <div className="race-head">
              <span className="race-title">{race.name}</span>
              <span className="race-meta">{race.date}・{race.course} {race.number}R</span>
            </div>
            {race.entries.map((e) => {
              const sync = syncs.get(e.horseId)!;
              const theme = dayTheme(e.horseBirth, race.date);
              return (
                <article className="horse-card" key={e.horseId}>
                  <header className="horse-head">
                    <div>
                      <div className="horse-name">{e.horseName}</div>
                      <div className="horse-sub">{e.post}番・鞍上 {e.jockeyName}・「{theme.word}」・LP{lifePath(e.horseBirth)}・{sunSign(e.horseBirth).ja}</div>
                    </div>
                  </header>
                  <div className="ministats">
                    <div className="stat">
                      <div className={`stat-num sync-inline-${sync.tier}`}>{sync.score.toFixed(1)}</div>
                      <div className="stat-key">シンクロ度</div>
                    </div>
                    <div className="stat">
                      <div className="stat-num stat-sign">{sync.pattern.label}</div>
                      <div className="stat-key">集合意識との関係</div>
                    </div>
                  </div>
                  <Link className="quad-btn" href={`/reading?race=${race.id}&horse=${e.horseId}`}
                    style={{ textDecoration: "none", textAlign: "center", display: "block" }}>
                    この馬とあなたの物語を読む
                  </Link>
                </article>
              );
            })}
          </section>
        );
      })}
      {FOOTER}
    </>
  );
}

function RacesBody() {
  const params = useSearchParams();
  const initRace = params.get("race");
  const initHorse = params.get("horse");
  const [birth, setBirth] = useState<string | null>(null);
  const [api, setApi] = useState<ApiDayRecommendations | null>(null);
  const [checked, setChecked] = useState(false);

  const [userOff, setUserOff] = useState(false);
  useEffect(() => {
    const b = localStorage.getItem("birthdate");
    const eff = effectiveBirth(b, birthdateEnabled());
    setBirth(eff);
    setUserOff(!!b && !eff);
    fetchDayRecommendations(eff).then((d) => { setApi(d); setChecked(true); });
  }, []);

  return (
    <main>
      {api && api.items.length > 0
        ? <ApiRaces api={api} hasBirth={!!birth} userOff={userOff}
            initRace={initRace} initHorse={initHorse} />
        : checked ? <MockRaces birth={birth} /> : null}
    </main>
  );
}

export default function Races() {
  return (
    <Suspense fallback={<main />}>
      <RacesBody />
    </Suspense>
  );
}
