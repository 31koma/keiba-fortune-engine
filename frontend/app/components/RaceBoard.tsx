"use client";
// 出馬表ボード。2026-08-16 オーナー指定で netkeiba の出馬表と同じ構造に統一した。
//   「場タブ → Rタブ → 1行1頭の表」。画面を移動せずタブだけで全レースを見て回れる。
//
// なぜ作り替えたか(オーナー談 2026-08-16):
//   「いまのアプリの見方は気に入っていない。ややこしいから」
//   旧画面は 場一覧 → レース一覧 → 馬一覧 の3階層ドリルダウンで、
//   さらに1頭あたり 主・客・本・数・収・理・調・騎 の8指標を横に並べていた。
//   → **一覧に出す数字は「合」と、その材料である 収・理・調・騎 の4つだけにする。**
//     主・客・本・数は選定に使っていないので詳細シートへ送る。
//   数字を減らすこと自体が改善であって、削った情報は詳細で見られる。
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ApiRecoItem, ApiRaceGroup, WAKU_STYLE, wakuOf,
} from "@/lib/api";
import { bandFor } from "@/lib/synchroModes";
import { fiftyOf, topByFifty } from "@/lib/fifty";

const SURFACE: Record<string, string> = { turf: "芝", dirt: "ダ", jump: "障" };

// 脚質コード。**2026-08-16に実測で裏取り済み**: 8/16のSRB(1コーナー通過順)と
// 突き合わせると、1→4の順で相対位置が 0.286 / 0.390 / 0.540 / 0.697 と単調に後ろへ下がる。
const KYAKU: Record<number, string> = { 1: "逃", 2: "先", 3: "差", 4: "追" };

// 発売締切時刻。**出典: JRA / 競馬ブック(2022-07-16よりネット投票は2分前→1分前へ変更)**
//   ネット投票(即PAT・A-PAT)  : 発走の1分前
//   競馬場・WINSの窓口        : 発走の2分前
//   電話・JRAダイレクト        : 発走の5分前
//   WIN5                     : 最初の対象レースの発走の10分前(JRAダイレクトは15分前)
// 画面にはいちばん遅い「ネット投票」を出す。他の買い方は説明の中に書く。
const DEADLINE_MIN = 1;

function deadlineOf(startTime: string | null): string | null {
  if (!startTime || !/^\d{1,2}:\d{2}$/.test(startTime)) return null;
  const [h, m] = startTime.split(":").map(Number);
  const t = h * 60 + m - DEADLINE_MIN;
  if (t < 0) return null;
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}

/** 締切までの残り。今日のレースのときだけ出す(過去日を見ているときは出さない) */
function useCountdown(targetDate: string, startTime: string | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 20000);
    return () => clearInterval(id);
  }, []);
  if (!startTime) return null;
  const today = new Date(now);
  const ymd = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`
    + `-${String(today.getDate()).padStart(2, "0")}`;
  if (ymd !== targetDate) return null;              // 今日でなければ出さない
  const [h, m] = startTime.split(":").map(Number);
  const dl = new Date(today);
  dl.setHours(h, m - DEADLINE_MIN, 0, 0);
  const diff = Math.floor((dl.getTime() - now) / 60000);
  if (diff < 0) return "締切";
  if (diff === 0) return "まもなく締切";
  if (diff < 60) return `締切まで${diff}分`;
  return `締切まで${Math.floor(diff / 60)}時間${diff % 60}分`;
}



// 列見出しの説明(カーソルを乗せる/タップすると出る)。
// 2026-08-16 オーナー「合 収 理 調 騎 脚 想 激 これよくわからん。カーソル持っていったら説明で」。
// 数字を出すなら何を数えたかを添える、という編集規範に従い、実測値もここに書く。
const TIPS: Record<string, { title: string; body: string }> = {
  waku: { title: "枠", body: "JRAの枠番。8枠まで。多頭数のレースでは大きい枠に複数頭が入ります。" },
  no: { title: "馬番", body: "ゲートの番号。左(内)から順に1番。" },
  nm: { title: "馬名 / 騎手", body: "上が馬名、下が鞍上。行をタップすると、その馬の詳しい鑑定が開きます。" },
  fifty: {
    title: "合 — 50/50総合",
    body: "スピ(収)50% × 物理(理・調・騎の平均)50%。おすすめと✦はこの点で選んでいます。"
      + "迷ったら、まずこの数字がいちばん濃い馬。",
  },
  oshi: {
    title: "収 — 収束度",
    body: "星と戦績が同じ方向を向いたときの最終評価。オッズを使っていないので、"
      + "市場と別のことを言えます。高いグループが走りやすい数字であって、1頭を当てる数字ではありません。",
  },
  idm: { title: "理 — 能力", body: "馬の実力(JRDBのIDM)。その日の最高=10・最低=0で10点満点に換算しています。" },
  cyokyo: { title: "調 — 仕上がり", body: "調教の良さ(調教指数)。同じくその日の中で10点満点に換算。" },
  joc: { title: "騎 — 騎手", body: "鞍上の腕(騎手指数)。同じくその日の中で10点満点に換算。" },
  kyaku: {
    title: "脚 — 脚質",
    body: "どこを走るつもりの馬か。逃=先頭 / 先=前め / 差=中団から / 追=後方から。"
      + "JRDBの想定です(8/16の実際のコーナー通過順と突き合わせて向きを確認済み)。",
  },
  goal: {
    title: "想 — 想定ゴール順位",
    body: "JRDBが予想している着順。1位は金色にしています。"
      + "12開催日5612頭の実測では、想定1位の馬は勝26.6%・複54.3%(全馬は勝7.7%・複22.9%)。",
  },
  gekiso: {
    title: "激 — 激走指数",
    body: "一発がありそうかの目安。12開催日の実測では、200以上で勝13.8%、100未満で勝4.1%。",
  },
  odds: { title: "単勝", body: "前日時点の単勝オッズ。当日のオッズではありません。" },
  pop: { title: "人気", body: "前日基準の人気順。1〜3番人気には色を敷いています。" },
};

/** 見出しセル。カーソルを乗せる(スマホはタップ)と説明が出る */
function Th({ k, label, cls }: { k: string; label: string; cls: string }) {
  const t = TIPS[k];
  return (
    <th className={cls}>
      <button type="button" className="rb-h">
        {label}
        <span className="rb-tip" role="tooltip">
          <b>{t.title}</b>
          {t.body}
        </span>
      </button>
    </th>
  );
}

function Waku({ post, headCount }: { post: number | null; headCount: number }) {
  if (!post) return <td className="rb-waku" />;
  const st = WAKU_STYLE[wakuOf(post, headCount)];
  return (
    <td className="rb-waku">
      <span className="rb-waku-box" style={{
        background: st.bg, color: st.fg,
        border: st.border ? `1px solid ${st.border}` : "1px solid transparent",
      }}>{wakuOf(post, headCount)}</span>
    </td>
  );
}

/** 収・理・調・騎の小セル。色は点の高さ(bandFor)で全指標共通 */
function Cell({ v }: { v: number | null | undefined }) {
  if (v == null) return <td className="rb-m rb-m-none">—</td>;
  return <td className={`rb-m sync-inline-${bandFor(v).tier}`}>{v.toFixed(1)}</td>;
}

export default function RaceBoard({ groups, targetDate, onPick, initRaceId }: {
  groups: ApiRaceGroup[];
  targetDate: string;
  onPick: (it: ApiRecoItem) => void;
  initRaceId?: string | null;
}) {
  const courses = useMemo(() => {
    const seen: string[] = [];
    groups.forEach((g) => { if (!seen.includes(g.racecourse)) seen.push(g.racecourse); });
    return seen;
  }, [groups]);

  const initGroup = initRaceId ? groups.find((g) => g.race_id === initRaceId) : null;
  const [course, setCourse] = useState(initGroup?.racecourse ?? courses[0] ?? "");
  const courseRaces = useMemo(
    () => groups.filter((g) => g.racecourse === course)
      .slice().sort((a, b) => a.race_number - b.race_number),
    [groups, course]);
  const [raceId, setRaceId] = useState(initGroup?.race_id ?? courseRaces[0]?.race_id ?? "");

  // 場を切り替えたら、その場の同じR番号へ寄せる(なければ先頭)
  const prevCourse = useRef(course);
  useEffect(() => {
    if (prevCourse.current === course) return;
    const cur = groups.find((g) => g.race_id === raceId);
    const same = cur && courseRaces.find((g) => g.race_number === cur.race_number);
    setRaceId((same ?? courseRaces[0])?.race_id ?? "");
    prevCourse.current = course;
  }, [course, courseRaces, groups, raceId]);

  const race = groups.find((g) => g.race_id === raceId) ?? courseRaces[0];
  const headStart = race?.items?.[0]?.start_time ?? null;
  const deadline = deadlineOf(headStart);
  const left = useCountdown(targetDate, headStart);
  if (!race) return null;

  const rows = race.items.slice()
    .sort((a, b) => (a.post_number ?? 0) - (b.post_number ?? 0));
  const head = rows[0];
  const topId = topByFifty(race.items)?.horse_id;   // ✦=このレースの合トップ

  return (
    <div className="rb">
      {/* 場タブ */}
      <div className="rb-tabs rb-tabs-course" role="tablist" aria-label="開催場">
        {courses.map((c) => (
          <button key={c} role="tab" aria-selected={c === course}
            className={`rb-tab ${c === course ? "on" : ""}`}
            onClick={() => setCourse(c)}>{c}</button>
        ))}
      </div>

      {/* Rタブ(隠れ推しがいるレースには ✦) */}
      <div className="rb-tabs rb-tabs-race" role="tablist" aria-label="レース">
        {courseRaces.map((g) => (
          <button key={g.race_id} role="tab" aria-selected={g.race_id === race.race_id}
            className={`rb-rtab ${g.race_id === race.race_id ? "on" : ""}`}
            onClick={() => setRaceId(g.race_id)}>
            {g.race_number}R
            {g.items.some((it) => it.oshi?.hidden) && <i className="rb-dot" aria-hidden />}
          </button>
        ))}
      </div>

      {/* レース情報 */}
      <div className="rb-head">
        <span className="rb-rno">{race.race_number}R</span>
        <span className="rb-rname">
          {race.race_name && race.race_name !== "レース"
            ? race.race_name : `${race.racecourse}${race.race_number}R`}
        </span>
        {deadline && (
          <button type="button" className="rb-h rb-deadline">
            締切 {deadline}
            {left && <em className={left === "締切" ? "rb-left over" : "rb-left"}>{left}</em>}
            <span className="rb-tip" role="tooltip">
              <b>発売締切</b>
              画面に出しているのは<b style={{ display: "inline" }}>ネット投票(即PAT・A-PAT)</b>
              の締切で、発走の1分前です(2022年7月16日に2分前から変更)。
              買い方によって違います — 競馬場・WINSの窓口は発走の2分前、
              電話・JRAダイレクトは5分前。
              WIN5は最初の対象レースの発走の10分前(JRAダイレクトは15分前)。
              出典: JRA。変更されることがあるので、締め切り間際はJRA公式で確かめてください。
            </span>
          </button>
        )}
        <span className="rb-rmeta">
          {head?.start_time ? `${head.start_time}発走` : ""}
          {head?.distance ? ` / ${SURFACE[head.surface] ?? ""}${head.distance}m` : ""}
          {head?.head_count ? ` / ${head.head_count}頭` : ""}
          {` / ${targetDate}`}
        </span>
      </div>

      {/* 出馬表 */}
      <div className="rb-scroll">
        <table className="rb-table">
          <thead>
            <tr>
              <Th k="waku" label="枠" cls="rb-waku" />
              <Th k="no" label="馬番" cls="rb-no" />
              <Th k="nm" label="馬名 / 騎手" cls="rb-nm" />
              <Th k="fifty" label="合" cls="rb-fifty" />
              <Th k="oshi" label="収" cls="rb-m" />
              <Th k="idm" label="理" cls="rb-m" />
              <Th k="cyokyo" label="調" cls="rb-m" />
              <Th k="joc" label="騎" cls="rb-m" />
              <Th k="kyaku" label="脚" cls="rb-m rb-ext" />
              <Th k="goal" label="想" cls="rb-m rb-ext" />
              <Th k="gekiso" label="激" cls="rb-m rb-ext" />
              <Th k="odds" label="単勝" cls="rb-odds" />
              <Th k="pop" label="人気" cls="rb-pop" />
            </tr>
          </thead>
          <tbody>
            {rows.map((it) => {
              const f = fiftyOf(it);
              const ph = it.physical;
              const pop = ph?.pop_rank ?? null;
              return (
                <tr key={it.horse_id}
                  className={`rb-row ${it.horse_id === topId ? "top" : ""}`}
                  onClick={() => onPick(it)}>
                  <Waku post={it.post_number} headCount={it.head_count} />
                  <td className="rb-no">{it.post_number}</td>
                  <td className="rb-nm">
                    <span className="rb-hname">
                      {it.horse_id === topId && <span className="rb-star">✦</span>}
                      {it.horse_name}
                    </span>
                    <span className="rb-jockey">{it.jockey_name}</span>
                  </td>
                  <td className="rb-fifty">
                    {f == null
                      ? <span className="rb-m-none">—</span>
                      : <span className={`rb-fbadge sync-inline-${bandFor(f).tier}`}>
                          {f.toFixed(1)}
                        </span>}
                  </td>
                  <Cell v={it.oshi?.score} />
                  <Cell v={ph?.idm10} />
                  <Cell v={ph?.cyokyo10} />
                  <Cell v={ph?.joc10} />
                  <td className="rb-m rb-ext rb-kyaku">
                    {ph?.kyakushitsu ? KYAKU[ph.kyakushitsu] ?? "—" : "—"}
                  </td>
                  <td className={`rb-m rb-ext ${ph?.goal_rank === 1 ? "rb-hit" : ""}`}>
                    {ph?.goal_rank ?? "—"}
                  </td>
                  <td className="rb-m rb-ext">{ph?.gekiso_idx ?? "—"}</td>
                  <td className="rb-odds">{it.win_odds ? it.win_odds.toFixed(1) : "—"}</td>
                  <td className={`rb-pop ${pop && pop <= 3 ? `p${pop}` : ""}`}>
                    {pop ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="rb-legend">
        <b>✦</b>=このレースの「合」トップ(その行は金色)。<b>金の点</b>のついたRタブ=隠れ推しがいるレース。
        <b>見出しにカーソルを乗せる</b>(スマホはタップ)と、その列の説明が出ます。
        色は点の高さ: 金9以上 / 緑8台 / 青6〜7台 / 橙4〜5台 / 赤4未満。
        脚・想・激は参考値で、「合」の式には入れていません。
      </p>
    </div>
  );
}
