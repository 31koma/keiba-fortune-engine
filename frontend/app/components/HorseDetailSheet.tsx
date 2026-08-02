"use client";
// 馬詳細シート(下から出るパネル)。
// タブ=表示モード(lib/synchroModes.MODES)。要素の組合せを変えて再計算するだけの
// 汎用設計なので、将来の「詳細設定(要素ON/OFF)」はincludeを渡す口を足せばよい。
import Link from "next/link";
import { useState } from "react";
import { ApiRecoItem, WAKU_STYLE, wakuOf } from "@/lib/api";
import { bandFor, marketComparison, MODES, ModeResult, recompute } from "@/lib/synchroModes";

const SUUHI_SIGNALS: [string, string][] = [
  ["phase", "位相(流れの向き)"],
  ["rhythm", "律(周期の続き)"],
  ["resilience", "弾性(戻る力)"],
  ["keynote", "基調(波の高さ)"],
];

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

function CompBars({ result }: { result: ModeResult }) {
  return (
    <div style={{ marginTop: 14 }}>
      {result.used.map((u) => (
        <div className="comp-row" key={u.key}>
          <span className="comp-label">{u.label}</span>
          <span className="comp-bar"><span style={{ width: `${u.score * 10}%` }} /></span>
          <span className="comp-val">{u.score.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

function ScoreBox({ result, patternChip }: {
  result: ModeResult;
  patternChip?: { type: string; label: string } | null;
}) {
  return (
    <div className={`sync-box sync-${result.tier}`} style={{ marginTop: 0, padding: "18px 14px 14px" }}>
      <div className="sync-score" style={{ fontSize: 38 }}>
        {result.score.toFixed(1)}<span className="sync-max"> /10</span>
      </div>
      <div className="sync-word">{result.label}</div>
      {patternChip && (
        <div className={`pattern-chip pattern-${patternChip.type}`}>{patternChip.label}</div>
      )}
    </div>
  );
}

type ModeKey = keyof typeof MODES | "suuhi" | "oshi";

const TAB_DESCS: Record<string, string> = {
  suuhi: "戦績の流れと波形から読み解く数理評価です。",
  oshi: "星と戦績が同じ方向を向いたときの最終評価です。",
};

const PN_MODE_JA: Record<string, string> = {
  full: "全律(4信号)", trio: "三律(律を除く3信号)", solo: "単律(基調のみ)",
};

export default function HorseDetailSheet({ item, hasBirth, userOff = false, onClose }: {
  item: ApiRecoItem;
  hasBirth: boolean;
  userOff?: boolean;  // 誕生日は登録済みだが「鑑定に使用する」設定がOFF
  onClose: () => void;
}) {
  const [mode, setMode] = useState<ModeKey>("you_quad");
  const c = item.synchro.components;

  const result = mode === "suuhi" || mode === "oshi"
    ? recompute(c, MODES.you_quad.include)  // 未使用(数・収タブは独自表示)
    : recompute(c, MODES[mode].include);
  const mc = marketComparison(c);
  const pn = item.pattern_numerology;

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="detail-head">
          <div>
            <div className="detail-race">
              {item.racecourse}{item.race_number}R
              {item.start_time ? `・${item.start_time}発走` : ""}
            </div>
            <div className="detail-name">
              <Waku post={item.post_number} headCount={item.head_count} />
              {item.horse_name}
            </div>
            <div className="detail-sub">
              鞍上 {item.jockey_name}{item.win_odds ? `・単勝${item.win_odds}` : ""}
            </div>
          </div>
          <button className="detail-close" onClick={onClose} aria-label="閉じる">✕</button>
        </div>

        <div className="tabs">
          {(Object.keys(MODES) as ModeKey[]).map((k) => (
            <button key={k} className={mode === k ? "on" : ""} onClick={() => setMode(k)}>
              {MODES[k as keyof typeof MODES].label}
            </button>
          ))}
          <button className={mode === "suuhi" ? "on" : ""} onClick={() => setMode("suuhi")}>
            数
          </button>
          <button className={mode === "oshi" ? "on" : ""} onClick={() => setMode("oshi")}>
            収
          </button>
        </div>
        <p className="tab-desc" key={mode}>
          {mode === "suuhi" || mode === "oshi"
            ? TAB_DESCS[mode] : MODES[mode as keyof typeof MODES].desc}
        </p>

        {mode === "oshi" ? (
          <div className="tab-body">
            {!item.oshi ? (
              <p className="races-sub" style={{ textAlign: "center", marginTop: 8 }}>
                この開催データでは収束度を計算できませんでした。
              </p>
            ) : (
              <>
                <div className={`sync-box sync-${item.oshi.tier}`}
                  style={{ marginTop: 0, padding: "18px 14px 14px" }}>
                  <div className="sync-score" style={{ fontSize: 38 }}>
                    {item.oshi.score.toFixed(1)}<span className="sync-max"> /10</span>
                  </div>
                  <div className="sync-word">{item.oshi.label}</div>
                  {item.oshi.hidden && (
                    <div className="pattern-chip pattern-hidden">
                      {item.oshi.hidden.label_ja}
                    </div>
                  )}
                </div>
                <div style={{ marginTop: 14 }}>
                  <div className="comp-row">
                    <span className="comp-label">本質(純占術)</span>
                    <span className="comp-bar">
                      <span style={{ width: `${item.oshi.essence * 10}%` }} />
                    </span>
                    <span className="comp-val">{item.oshi.essence.toFixed(1)}</span>
                  </div>
                  <div className="comp-row">
                    <span className="comp-label">調律(戦績)</span>
                    <span className="comp-bar">
                      <span style={{
                        width: `${(item.oshi.choritsu ?? 0) * 10}%` }} />
                    </span>
                    <span className="comp-val">
                      {item.oshi.choritsu === null ? "—" : item.oshi.choritsu.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <div className="label" style={{ marginBottom: 6 }}>この馬に収束する読み</div>
                  {item.oshi.reasons.map((r) => (
                    <p className="pattern-line" key={r.id} style={{ marginTop: 6 }}>
                      {r.line}
                    </p>
                  ))}
                  {item.oshi.hidden && (
                    <p className="pattern-line" style={{ marginTop: 6 }}>
                      {item.oshi.hidden.line}
                    </p>
                  )}
                </div>
                <p className="sync-note">
                  収束度=本質(星)と数理(戦績)の収束を核に、検証で有効性が確認された
                  要素だけを段階的に組み込んでいく最終評価({item.oshi.version})。
                  オッズ・人気はスコアに使用していません
                  {item.oshi.confidence === "low"
                    ? "。走歴がごく少ないため、今回は控えめな参考値です"
                    : item.oshi.confidence === "medium"
                      ? "。走歴がやや少ないため、調律は中立へ寄せた値です"
                      : ""}。
                  検証前の仮説指標であり、レース結果の予測や馬券購入の推奨ではありません。
                </p>
              </>
            )}
          </div>
        ) : mode === "suuhi" ? (
          <div className="tab-body">
            {!pn || pn.insufficient ? (
              <p className="races-sub" style={{ textAlign: "center", marginTop: 8 }}>
                まだ読める走歴がありません(初出走の馬は走歴が積まれてから読めます)。
              </p>
            ) : (
              <>
                <div className={`sync-box sync-${bandFor(pn.score).tier}`}
                  style={{ marginTop: 0, padding: "18px 14px 14px" }}>
                  <div className="sync-score" style={{ fontSize: 38 }}>
                    {pn.score.toFixed(1)}<span className="sync-max"> /10</span>
                  </div>
                  <div className="sync-word">{pn.label}</div>
                </div>
                <div style={{ marginTop: 14 }}>
                  {SUUHI_SIGNALS.map(([key, label]) => (
                    pn.signals[key] !== undefined && (
                      <div className="comp-row" key={key}>
                        <span className="comp-label">{label}</span>
                        <span className="comp-bar">
                          <span style={{ width: `${pn.signals[key] * 10}%` }} />
                        </span>
                        <span className="comp-val">{pn.signals[key].toFixed(1)}</span>
                      </div>
                    )
                  ))}
                </div>
                <p className="sync-note">
                  直近{pn.runs_used}走の着順の並びから算出(調律理論 {pn.version}
                  {pn.mode && PN_MODE_JA[pn.mode] ? `・${PN_MODE_JA[pn.mode]}` : ""}
                  ・信頼度{Math.round(pn.confidence * 100)}%)。
                  理想は5走。走歴が少ない場合は読める信号だけで解析し、
                  信頼度に応じて中立へ寄せた控えめな値にしています。
                  オッズ・人気は使用していません。検証前の仮説指標であり、
                  レース結果の予測ではありません。
                </p>
              </>
            )}
          </div>
        ) : mode === "you_quad" && !hasBirth ? (
          <div className="tab-body">
            <ScoreBox result={result} patternChip={{
              type: item.synchro.pattern.type, label: item.synchro.pattern.label_ja }} />
            <CompBars result={result} />
            {userOff ? (
              <p className="sync-note">
                「誕生日を鑑定に使用する」設定がOFFのため、「あなた」を除いた
                客観鑑定を表示しています。入口の設定でいつでも戻せます。
              </p>
            ) : (
              <>
                <p className="sync-note">
                  まだ生年月日が未登録のため「あなた」の軸は含まれていません。
                  登録すると、あなたの日運を織り込んだ自分だけの値になります。
                </p>
                <Link href="/" className="cta-sub"
                  style={{ display: "block", textAlign: "center", textDecoration: "none" }}>
                  入口で生年月日を登録する
                </Link>
              </>
            )}
          </div>
        ) : mode === "market_compare" ? (
          <div className="tab-body">
            <div className="mc-grid">
              <div className="mc-cell">
                <div className="mc-key">純粋な流れ</div>
                <div className="mc-val mc-gold">{mc.pure.toFixed(1)}</div>
              </div>
              <div className="mc-cell">
                <div className="mc-key">市場評価</div>
                <div className="mc-val">{mc.market.toFixed(1)}</div>
              </div>
              <div className="mc-cell">
                <div className="mc-key">差分</div>
                <div className="mc-val">{mc.gap > 0 ? `+${mc.gap.toFixed(1)}` : mc.gap.toFixed(1)}</div>
              </div>
            </div>
            <p className="mc-headline">「{mc.headline}」</p>
            <p className="pattern-line">{mc.line}</p>
            <CompBars result={result} />
            <p className="sync-note">
              純粋な流れ=馬・騎手・レース日だけで再計算した値
              (あなた・市場は含みません)。
              勝率・期待値・回収率の予測ではありません。
            </p>
          </div>
        ) : (
          <div className="tab-body">
            <ScoreBox result={result}
              patternChip={mode === "you_quad"
                ? { type: item.synchro.pattern.type, label: item.synchro.pattern.label_ja }
                : null} />
            <CompBars result={result} />
          </div>
        )}
      </div>
    </div>
  );
}
