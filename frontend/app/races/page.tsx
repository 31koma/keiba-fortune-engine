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
import { fiftyOf, topByFifty } from "@/lib/fifty";
import { birthdateEnabled, effectiveBirth } from "@/lib/settings";

/** 合バッジ(馬行の右上・レース一覧の右)。合の定義と根拠は lib/fifty.ts */
function FiftyBadge({ it }: { it: ApiRecoItem }) {
  const f = fiftyOf(it);
  if (f == null) return null;
  return (
    <span className={`ih-sync sync-inline-${bandFor(f).tier}`}>合{f.toFixed(1)}</span>
  );
}

/** 一覧の4指標セル */
function Metric({ k, v, tier, digits = 1 }: {
  k: string; v: number | null; tier: string | null; digits?: number;
}) {
  return (
    <span className="metric">
      <span className="metric-key">{k}</span>
      <span className={`metric-val ${tier ? `sync-inline-${tier}` : "metric-none"}`}>
        {v === null ? "—" : v.toFixed(digits)}
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
  const ph = it.physical;
  return (
    <span className="metric-strip">
      <Metric k="主" v={s.score} tier={s.tier} />
      <Metric k="客" v={kyak.score} tier={kyak.tier} />
      <Metric k="本" v={hon.score} tier={hon.tier} />
      <Metric k="数" v={pnOk ? pn.score : null}
        tier={pnOk ? bandFor(pn.score).tier : null} />
      <Metric k="収" v={oshi ? oshi.score : null} tier={oshi ? oshi.tier : null} />
      <Metric k="理" v={ph?.idm10 ?? null}
        tier={ph?.idm10 != null ? bandFor(ph.idm10).tier : null} />
      <Metric k="調" v={ph?.cyokyo10 ?? null}
        tier={ph?.cyokyo10 != null ? bandFor(ph.cyokyo10).tier : null} />
      <Metric k="騎" v={ph?.joc10 ?? null}
        tier={ph?.joc10 != null ? bandFor(ph.joc10).tier : null} />
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
        <span className="win5-meta">合(スピ50×物理50)順・3×3×3×3×3=243通り</span>
      </div>
      {legs.map((g, i) => {
        const keyOf = (x: ApiRecoItem) =>
          fiftyOf(x) ?? recompute(x.synchro.components, MODES.quad.include).score;
        const top3 = g.items
          .slice()
          .sort((a, b) => keyOf(b) - keyOf(a))
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
                const f = fiftyOf(it);
                const k = recompute(it.synchro.components, MODES.quad.include);
                const v = f ?? k.score;
                const tier = f != null ? bandFor(f).tier : k.tier;
                return (
                  <button className="win5-pick" key={it.horse_id} onClick={() => onPick(it)}>
                    <span className="win5-post">{it.post_number}</span>
                    <span className="win5-hname">{it.horse_name}</span>
                    <span className={`win5-score sync-inline-${tier}`}>
                      {v.toFixed(1)}
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
    シンクロ度=占術4者の調和+集合意識(オッズ)の共鳴(synchro_v0・検証継続中の仮説)。
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
  const dayPick = useMemo(() => topByFifty(api.items), [api.items]);
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
    const topId = topByFifty(race.items)?.horse_id; // ✦=合(50/50総合)トップ
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
        <p className="ipat-hint">✦=このレースの「合」トップ(合=スピ50%×物理50%)。馬をタップすると詳細が開きます</p>
        <p className="ipat-hint" style={{ fontWeight: 700 }}>
          見方: まず「合」。あとは濃い色を数える(1〜3番人気は点差を見ない)。「収」と「理」が両方濃い馬がねらい目。
        </p>
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
                <FiftyBadge it={it} />
                <span className="ih-odds">{it.win_odds ? `単${it.win_odds}` : ""}</span>
              </span>
              <MetricStrip it={it} />
            </button>
          );
        })}
        <p className="ipat-hint">
          合=スピ(収)50%×物理(理・調・騎の平均)50%の総合点。おすすめ・✦・レース一覧の数字はこの点で選ぶ /
          主=あなたを含めた総合評価 / 客=あなたを除いた客観評価 /
          本=馬・騎手・レース日の本質評価 / 数=戦績の流れと波形を読む数理評価 /
          収=星と戦績が同じ方向を向いたときの最終評価(収束・オッズ不使用) /
          理=能力(JRDB IDM) / 調=仕上がり(調教指数) / 騎=鞍上の腕(騎手指数)。
          物理3指標は星と同じ10点満点(本日の最高=10・最低=0)。星と混ぜず並べて見る。
          色は全指標共通で点の高さ: 金=9以上 / 緑=8台 / 青=6〜7台 / 橙=4〜5台 / 赤=4未満
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
          const pick = topByFifty(g.items);
          const pf = pick ? fiftyOf(pick) : null;
          const hasHidden = g.items.some((it) => it.oshi?.hidden);
          return (
            <button key={g.race_id} className="ipat-race" onClick={() => setRaceId(g.race_id)}>
              <span className="ir-no">{g.race_number}R</span>
              <span className="ir-name">
                {hasHidden && <span className="ih-star">✦ </span>}
                {g.race_name && g.race_name !== "レース" ? g.race_name : ""}
              </span>
              <span className="ir-right">
                {pf != null
                  ? <span className={`ih-sync sync-inline-${bandFor(pf).tier}`}>{pf.toFixed(1)}</span>
                  : top && <span className={`ih-sync sync-inline-${top.synchro.tier}`}>{top.synchro.score.toFixed(1)}</span>}
                <span className="ir-time">{top?.start_time ?? ""}</span>
              </span>
            </button>
          );
        })}
        <p className="ipat-hint">右の数字は各レースの推しトップの「合」(スピ50%×物理50%)。✦=隠れ推しがいるレース</p>
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
      {dayPick && (
        <button className="ipat-reco" onClick={() => {
          setCourse(dayPick.racecourse);
          setRaceId(dayPick.race_id);
          setDetail(dayPick);
        }}>
          ✦ この日のおすすめ: {dayPick.racecourse}{dayPick.race_number}R
          {" "}{dayPick.horse_name}
          <span className={`ih-sync sync-inline-${bandFor(fiftyOf(dayPick)!).tier}`}>
            合{fiftyOf(dayPick)!.toFixed(1)}
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
