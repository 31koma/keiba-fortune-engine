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
              <th className="rb-waku">枠</th>
              <th className="rb-no">馬番</th>
              <th className="rb-nm">馬名 / 騎手</th>
              <th className="rb-fifty">合</th>
              <th className="rb-m">収</th>
              <th className="rb-m">理</th>
              <th className="rb-m">調</th>
              <th className="rb-m">騎</th>
              <th className="rb-m rb-ext" title="脚質(JRDB)">脚</th>
              <th className="rb-m rb-ext" title="JRDBの想定ゴール順位">想</th>
              <th className="rb-m rb-ext" title="激走指数(JRDB)">激</th>
              <th className="rb-odds">単勝</th>
              <th className="rb-pop">人気</th>
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
        <b>✦</b>=このレースの「合」トップ。<b>合</b>=スピ(収)50%×物理(理・調・騎)50%。
        馬をタップすると、主・客・本・数や展開・適性を含めた詳細が開きます。
        色は点の高さ: 金9以上 / 緑8台 / 青6〜7台 / 橙4〜5台 / 赤4未満。人気は前日基準人気。
        <br />
        <b>脚</b>=脚質(逃・先・差・追) / <b>想</b>=JRDBの想定ゴール順位 /
        <b>激</b>=激走指数。この3つは「合」には入れていない参考値です。
        12開催日5612頭の実測では、想定ゴール1位の馬は勝26.6%・複54.3%(全馬は7.7%・22.9%)、
        激走指数は200以上で勝13.8%・100未満で勝4.1%でした。
      </p>
    </div>
  );
}
