"use client";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import HorseDetailSheet from "../components/HorseDetailSheet";
import RaceBoard from "../components/RaceBoard";
import PageNav from "../components/PageNav";
import { MOCK_RACES } from "@/lib/mock";
import { dayTheme, lifePath, sunSign } from "@/lib/preview";
import { computeSynchro } from "@/lib/synchro";
import {
  ApiDayRecommendations, ApiRecoItem, fetchDayRecommendations, groupByRace,
} from "@/lib/api";
import { bandFor, MODES, recompute } from "@/lib/synchroModes";
import { fiftyOf, topByFifty } from "@/lib/fifty";
import { birthdateEnabled, effectiveBirth } from "@/lib/settings";

// 一覧に出す数字は「合」と、その材料の 収・理・調・騎 の4つだけ(RaceBoard)。
// 主・客・本・数は選定に使っていないので詳細シート(HorseDetailSheet)へ送った。
// 2026-08-16 オーナー指定「いまの見方はややこしい」。数字を減らすこと自体が改善。

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

// ---------- 実データ: 出馬表ボード(場タブ → Rタブ → 表) ----------
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

  const [detail, setDetail] = useState<ApiRecoItem | null>(initItem);
  const [jumpTo, setJumpTo] = useState<string | null>(initItem?.race_id ?? null);

  const dayFifty = dayPick ? fiftyOf(dayPick) : null;

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

      {dayPick && dayFifty != null && (
        <button className="ipat-reco" onClick={() => {
          setJumpTo(dayPick.race_id);
          setDetail(dayPick);
        }}>
          ✦ この日のおすすめ: {dayPick.racecourse}{dayPick.race_number}R
          {" "}{dayPick.horse_name}
          <span className={`ih-sync sync-inline-${bandFor(dayFifty).tier}`}>
            合{dayFifty.toFixed(1)}
          </span>
        </button>
      )}

      <RaceBoard groups={groups} targetDate={api.target_date}
        initRaceId={jumpTo} onPick={setDetail} />

      <Win5Section groups={groups} onPick={(it) => {
        setJumpTo(it.race_id);
        setDetail(it);
      }} />
      {FOOTER}
      {detail && (
        <HorseDetailSheet item={detail} hasBirth={hasBirth} userOff={userOff}
          onClose={() => setDetail(null)} />
      )}
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
    <main className="main-wide">
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
