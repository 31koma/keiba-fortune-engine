"use client";
// 過去レースを見る — 「レースを見る」と同じドリルダウン構成の過去版。
// 違いは3点だけ: 対象が過去開催 / 結果が確定している / 各馬に確定着順を表示する。
// レース前評価は保存済みスナップショットのみ表示し、後から再計算した値は出さない。
import { Suspense, useEffect, useMemo, useState } from "react";
import PageNav from "../components/PageNav";
import {
  ApiPastDay, ApiPastRaceDetail, ApiPastRaces, ApiPastRaceSummary,
  fetchPastRaceDetail, fetchPastRaces, WAKU_STYLE, wakuOf,
} from "@/lib/api";
import { isPremium } from "@/lib/settings";

const MEDAL = ["", "🥇", "🥈", "🥉"];

const FOOTER = (
  <footer>
    過去レースの表示は、レース前に保存された評価と確定結果の照合(検証)です。
    <br />
    的中の約束や結果の予測ではなく、馬券購入の推奨でもありません。
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

const fmtDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  const wd = "日月火水木金土"[new Date(y, m - 1, d).getDay()];
  return `${y}年${m}月${d}日(${wd})`;
};

// 星読みターフは複勝(3着以内)重視 — 通常モードの着順表示は3着まで。
// 4着以下の詳細(何着か)はプレミアム限定で、通常は「4着以下」とだけ示す。
function ChakuBadge({ chaku, status, premium }: {
  chaku: number | null; status: string | null; premium: boolean;
}) {
  if (status) return <span className="chaku-badge chaku-ijo">{status}</span>;
  if (chaku === null) return <span className="chaku-badge chaku-none">—</span>;
  if (chaku <= 3) {
    return (
      <span className={`chaku-badge medal-${chaku}`}>
        {MEDAL[chaku]}{chaku}着
      </span>
    );
  }
  if (premium) return <span className="chaku-badge">確定{chaku}着</span>;
  return <span className="chaku-badge chaku-out">4着以下</span>;
}

// ---------- レース詳細(馬一覧+確定結果) ----------
function PastRaceDetail({ raceId, onBack }: { raceId: string; onBack: () => void }) {
  const [data, setData] = useState<ApiPastRaceDetail | null>(null);
  const [checked, setChecked] = useState(false);
  const [premium, setPremium] = useState(false);
  useEffect(() => {
    setPremium(isPremium());
    fetchPastRaceDetail(raceId).then((d) => { setData(d); setChecked(true); });
  }, [raceId]);

  if (!checked) return <PageNav onBack={onBack} />;
  if (!data) {
    return (
      <>
        <PageNav onBack={onBack} />
        <p className="races-sub" style={{ marginTop: 20 }}>
          レース情報を取得できませんでした。
        </p>
      </>
    );
  }

  const { race, results, snapshot } = data;
  const top3 = (results ?? []).filter((r) => r.chaku !== null && r.chaku <= 3)
    .sort((a, b) => (a.chaku! - b.chaku!));

  return (
    <>
      <PageNav onBack={onBack} />
      <div className="race-head" style={{ marginTop: 14 }}>
        <span className="race-title">
          {race.race_name && race.race_name !== "レース"
            ? race.race_name : `${race.racecourse}${race.race_number}R`}
        </span>
        <span className="race-meta">
          {fmtDate(race.date)}・{race.racecourse}{race.race_number}R
          ・{race.surface}{race.distance}m・{race.head_count}頭
          {results ? "・結果確定" : "・結果未取得"}
        </span>
      </div>

      {top3.length > 0 && (
        <section className="podium">
          <div className="podium-title">実際の結果</div>
          {top3.map((r) => (
            <div className="pod-row" key={r.horse_id}>
              <span className={`pod-medal medal-${r.chaku}`}>
                {MEDAL[r.chaku!]}{r.chaku}着
              </span>
              <Waku post={r.post_number} headCount={race.head_count} />
              <span className="pod-name">{r.horse_name}</span>
              <span className="pod-meta">
                {r.ninki ? `${r.ninki}人気` : ""}
                {r.odds_final ? `・単${r.odds_final}` : ""}
              </span>
            </div>
          ))}
        </section>
      )}

      {snapshot ? (
        <>
          <p className="ipat-hint">
            星読み順位({snapshot.metric_label}順)と確定着順の見比べです。
            評価は {snapshot.saved_at} に保存されたレース前のものです。
          </p>
          {snapshot.items.map((it) => (
            <div key={it.horse_id ?? it.rank} className="ipat-horse ih-col past-row">
              <span className="ih-top">
                <span className="yomi-rank">{it.rank}位</span>
                <Waku post={it.post_number} headCount={race.head_count} />
                <span className="ih-main">
                  <span className="ih-name">{it.horse_name}</span>
                  <span className="ih-sub">
                    {it.jockey_name}
                    {it.win_odds ? `・前日単${it.win_odds}` : ""}
                  </span>
                </span>
                <span className={`ih-sync sync-inline-${it.tier}`}>
                  {it.score.toFixed(1)}
                </span>
                <ChakuBadge chaku={it.chaku} status={it.status} premium={premium} />
              </span>
            </div>
          ))}
          <p className="ipat-hint">
            {snapshot.metric_label}=レース前に保存された評価(
            {snapshot.rules_ver ?? "旧版"}・オッズは
            {snapshot.metric === "oshi" ? "不使用" : "集合意識として参照"})。
            確定着順はJRDB成績データ由来です。
            {!premium && "星読みターフは複勝(3着以内)重視のため、着順表示は3着まで。"
              + "4着以下の詳細表示はプレミアム(準備中)限定です。"}
          </p>
        </>
      ) : (
        <>
          <p className="races-sub" style={{ marginTop: 18 }}>
            {data.snapshot_note ?? "このレースは、レース前の星読み評価が保存されていません。"}
            {results ? " 確定結果のみ表示しています。" : ""}
          </p>
          {results && (
            <div style={{ marginTop: 10 }}>
              {(premium ? results
                : results.filter((r) => r.chaku !== null && r.chaku <= 3))
                .map((r) => (
                <div key={r.horse_id} className="ipat-horse ih-col past-row">
                  <span className="ih-top">
                    <Waku post={r.post_number} headCount={race.head_count} />
                    <span className="ih-main">
                      <span className="ih-name">{r.horse_name}</span>
                      <span className="ih-sub">
                        {r.ninki ? `${r.ninki}人気` : ""}
                        {r.odds_final ? `・単${r.odds_final}` : ""}
                      </span>
                    </span>
                    <ChakuBadge chaku={r.chaku} status={r.status} premium={premium} />
                  </span>
                </div>
              ))}
              {!premium && (
                <p className="ipat-hint">
                  星読みターフは複勝(3着以内)重視のため、着順表示は3着まで。
                  4着以下の詳細表示はプレミアム(準備中)限定です。
                </p>
              )}
            </div>
          )}
        </>
      )}
      {FOOTER}
    </>
  );
}

// ---------- ドリルダウン(日付 → 場 → レース → 馬) ----------
function PastBody() {
  const [api, setApi] = useState<ApiPastRaces | null>(null);
  const [checked, setChecked] = useState(false);
  const [day, setDay] = useState<ApiPastDay | null>(null);
  const [course, setCourse] = useState<string | null>(null);
  const [raceId, setRaceId] = useState<string | null>(null);

  useEffect(() => {
    fetchPastRaces().then((d) => { setApi(d); setChecked(true); });
  }, []);

  const courses = useMemo(() => {
    if (!day) return [] as [string, ApiPastRaceSummary[]][];
    const m = new Map<string, ApiPastRaceSummary[]>();
    day.races.forEach((r) => {
      m.set(r.racecourse, [...(m.get(r.racecourse) ?? []), r]);
    });
    return Array.from(m.entries());
  }, [day]);

  if (!checked) return <main />;
  if (!api || api.days.length === 0) {
    return (
      <main>
        <PageNav />
        <section className="races-lead">
          <p className="races-q">過去レース</p>
          <p className="races-sub">
            表示できる過去レースがまだありません。バックエンドAPIの起動と、
            JRDBデータ(成績ファイル)の取得状況を確認してください。
          </p>
        </section>
        {FOOTER}
      </main>
    );
  }

  // --- 馬一覧(レース選択済み) ---
  if (raceId) {
    return (
      <main>
        <PastRaceDetail raceId={raceId} onBack={() => setRaceId(null)} />
      </main>
    );
  }

  // --- レース一覧(場選択済み) ---
  if (day && course) {
    const list = courses.find(([c]) => c === course)?.[1] ?? [];
    return (
      <main>
        <PageNav onBack={() => setCourse(null)} />
        <div className="race-head" style={{ marginTop: 14 }}>
          <span className="race-title">{course}</span>
          <span className="race-meta">{fmtDate(day.date)}・{list.length}レース</span>
        </div>
        {list.map((r) => (
          <button key={r.race_id} className="ipat-race" onClick={() => setRaceId(r.race_id)}>
            <span className="ir-no">{r.race_number}R</span>
            <span className="ir-name">
              {r.race_name && r.race_name !== "レース" ? r.race_name : ""}
              <span className="ih-sub" style={{ display: "inline", marginLeft: 6 }}>
                {r.surface}{r.distance}m
              </span>
            </span>
            <span className="ir-right">
              {r.has_results && <span className="past-chip">結果確定</span>}
              {r.has_snapshot && <span className="past-chip chip-snap">評価あり</span>}
            </span>
          </button>
        ))}
        <p className="ipat-hint">
          「評価あり」=レース前に保存された星読み評価が残っているレースです
        </p>
        {FOOTER}
      </main>
    );
  }

  // --- 場一覧(日付選択済み) ---
  if (day) {
    return (
      <main>
        <PageNav onBack={() => setDay(null)} />
        <div className="race-head" style={{ marginTop: 14 }}>
          <span className="race-title">{fmtDate(day.date)}</span>
          <span className="race-meta">{day.races.length}レース</span>
        </div>
        {courses.map(([name, list]) => (
          <button key={name} className="ipat-course" onClick={() => setCourse(name)}>
            <span>{name}</span>
            <span className="ic-meta">{list.length}レース ›</span>
          </button>
        ))}
        {FOOTER}
      </main>
    );
  }

  // --- 日付一覧 ---
  return (
    <main>
      <PageNav />
      <section className="races-lead">
        <p className="races-q">過去レースを見る</p>
        <p className="races-sub">
          過去に開催されたレースの、レース前の星読み評価と確定した着順を見比べられます。
          新しい開催日から順に表示しています。
        </p>
      </section>
      {api.days.map((d) => {
        const nSnap = d.races.filter((r) => r.has_snapshot).length;
        const confirmed = d.races.some((r) => r.has_results);
        return (
          <button key={d.date} className="ipat-course" onClick={() => setDay(d)}>
            <span>{fmtDate(d.date)}</span>
            <span className="ic-meta">
              {confirmed ? "結果確定・" : ""}
              {nSnap > 0 ? `評価あり${nSnap}R・` : ""}
              {d.races.length}レース ›
            </span>
          </button>
        );
      })}
      {FOOTER}
    </main>
  );
}

export default function Past() {
  return (
    <Suspense fallback={<main />}>
      <PastBody />
    </Suspense>
  );
}
