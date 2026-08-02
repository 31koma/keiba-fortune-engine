"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import BirthdateModal from "../components/BirthdateModal";
import { dayTheme, lifePath, previewLine, sunSign } from "@/lib/preview";
import { YOU } from "@/lib/you";
import {
  ApiCalendarDay, ApiCycle, ApiHumanFortune, ApiMonthCalendar,
  fetchHumanFortune, fetchMonthCalendar,
} from "@/lib/api";

// ---------- 運の流れ(今日/今月/今年) ----------
type FlowTab = "day" | "month" | "year";

const FLOW_TABS: { key: FlowTab; label: string }[] = [
  { key: "day", label: "今日を見る" },
  { key: "month", label: "月を見る" },
  { key: "year", label: "年を見る" },
];

const FLOW_META: Record<FlowTab, {
  title: string; roleLine: string;
  theme: (c: ApiCycle) => string;
}> = {
  day: { title: "今日のあなた", roleLine: "前景 — 当日の流れ。いちばん手前で動く数字です",
    theme: (c) => c.day_theme },
  month: { title: "今月のあなた", roleLine: "中景 — 中期の流れ。今月の過ごし方の基調です",
    theme: (c) => c.month_theme },
  year: { title: "今年のあなた", roleLine: "背景 — 9年サイクルの現在地。一年全体の基調です",
    theme: (c) => c.year_theme },
};

function CycleDots({ value }: { value: number }) {
  if (value < 1 || value > 9) return null; // マスターナンバー等は数字表示のみ
  return (
    <div className="cycle-dots" aria-label={`9年サイクルの${value}年目`}>
      {Array.from({ length: 9 }, (_, i) => (
        <span key={i} className={`cycle-dot ${i + 1 === value ? "on" : ""}`}>
          {i + 1 === value ? value : ""}
        </span>
      ))}
    </div>
  );
}

// ---------- 月間カレンダー(日別パーソナルデー) ----------
const WEEK_JA = ["月", "火", "水", "木", "金", "土", "日"];

function MonthCalendar({ birth }: { birth: string }) {
  const now = new Date();
  const [ym, setYm] = useState<{ y: number; m: number }>(
    { y: now.getFullYear(), m: now.getMonth() + 1 });
  const [cal, setCal] = useState<ApiMonthCalendar | null>(null);
  const [sel, setSel] = useState<ApiCalendarDay | null>(null);
  const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

  useEffect(() => {
    setCal(null); setSel(null);
    fetchMonthCalendar(birth, ym.y, ym.m).then((c) => {
      setCal(c);
      if (c) setSel(c.days.find((d) => d.date === todayIso) ?? null);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [birth, ym]);

  const move = (diff: number) => {
    setYm((p) => {
      const m0 = p.m - 1 + diff;
      return { y: p.y + Math.floor(m0 / 12), m: ((m0 % 12) + 12) % 12 + 1 };
    });
  };

  if (!cal) return <p className="flow-role">カレンダーを読み込み中…</p>;
  const lead = cal.days[0].weekday; // 0=月

  return (
    <div className="mcal">
      <div className="mcal-nav">
        <button onClick={() => move(-1)} aria-label="前の月">‹</button>
        <span className="mcal-title">{cal.year}年{cal.month}月</span>
        <button onClick={() => move(1)} aria-label="次の月">›</button>
      </div>
      <p className="flow-role" style={{ marginTop: 4 }}>
        {cal.month}月のあなた: {cal.personal_month.month_theme}(パーソナルマンス{cal.personal_month.value})
      </p>
      <div className="mcal-grid">
        {WEEK_JA.map((w) => <span className="mcal-w" key={w}>{w}</span>)}
        {Array.from({ length: lead }, (_, i) => <span key={`b${i}`} />)}
        {cal.days.map((d) => {
          const dayNo = Number(d.date.slice(8));
          const cls = [
            "mcal-day",
            d.date === todayIso ? "today" : "",
            sel?.date === d.date ? "sel" : "",
          ].join(" ");
          return (
            <button className={cls} key={d.date} onClick={() => setSel(d)}>
              <span className="mcal-date">{dayNo}</span>
              <span className="mcal-num">{d.value}</span>
            </button>
          );
        })}
      </div>
      {sel && (
        <p className="mcal-detail">
          {cal.month}月{Number(sel.date.slice(8))}日({WEEK_JA[sel.weekday]})
          — <b>{sel.value}</b>・{sel.day_theme}
        </p>
      )}
      <p className="flow-role">
        数字はその日のあなたのパーソナルデー。テーマの提示であり吉凶の断定ではありません
      </p>
    </div>
  );
}

function FortuneFlow({ fortune, birth }: { fortune: ApiHumanFortune; birth: string }) {
  const [tab, setTab] = useState<FlowTab>("day");
  const cycle: ApiCycle = tab === "day" ? fortune.personal_day
    : tab === "month" ? fortune.personal_month : fortune.personal_year;
  const meta = FLOW_META[tab];
  const m = cycle.meanings;
  const resonance = fortune.interpretation_parts?.resonance;
  return (
    <section className="you-sec today">
      <div className="theme-label">運の流れ</div>
      <div className="tabs flow-tabs">
        {FLOW_TABS.map((t) => (
          <button key={t.key} className={tab === t.key ? "on" : ""}
            onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>
      <div className="flow-num">
        <span className="flow-value">{cycle.value}</span>
        <span className="flow-kind">
          {tab === "day" ? "パーソナルデー" : tab === "month" ? "パーソナルマンス" : "パーソナルイヤー"}
        </span>
      </div>
      <div className="theme-word flow-word">{meta.theme(cycle)}</div>
      {tab === "year" && <CycleDots value={cycle.value} />}
      {m && m.keywords_ja.length > 0 && (
        <div className="flow-chips">
          {m.keywords_ja.map((k) => <span className="flow-chip" key={k}>{k}</span>)}
        </div>
      )}
      {m && (m.positive || m.negative) && (
        <dl className="flow-guide">
          {m.positive && (
            <div><dt>追い風</dt><dd>{m.positive}</dd></div>
          )}
          {m.negative && (
            <div><dt>気をつけたい傾向</dt><dd>{m.negative}</dd></div>
          )}
        </dl>
      )}
      <p className="flow-role">{meta.roleLine}</p>
      {tab === "month" && <MonthCalendar birth={birth} />}
      {resonance && <p className="flow-role">✦ {resonance.note}</p>}
      {tab === "day" && fortune.universal_day && (
        <p className="flow-role">
          この日全体の空気: {fortune.universal_day.day_theme}(ユニバーサルデー{fortune.universal_day.value})
        </p>
      )}
    </section>
  );
}

export default function You() {
  const [birth, setBirth] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [modal, setModal] = useState(false);
  const [fortune, setFortune] = useState<ApiHumanFortune | null>(null);
  useEffect(() => {
    setBirth(localStorage.getItem("birthdate"));
    setReady(true);
  }, []);
  useEffect(() => {
    if (!birth) return;
    const t = new Date();
    const iso = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
    fetchHumanFortune(birth, iso).then(setFortune);
  }, [birth]);

  if (!ready) return <main />;

  if (!birth) {
    return (
      <main>
        <Link href="/" className="back">← 入口へ戻る</Link>
        <section className="you-invite">
          <div className="theme-label">あなたを見る</div>
          <p className="races-q">まず、あなたの生まれ日から。</p>
          <p className="races-sub">
            このアプリの主役は馬だけではありません。あなたもレースという物語の参加者です。
            生年月日ひとつで、あなたの数字と星座が定まります。
          </p>
          <button className="cta" onClick={() => setModal(true)}>生年月日を登録する</button>
        </section>
        {modal && (
          <BirthdateModal onClose={() => setModal(false)}
            onSaved={(d) => { setBirth(d); setModal(false); }} />
        )}
      </main>
    );
  }

  const lp = lifePath(birth);
  const sign = sunSign(birth);
  const you = YOU[lp];
  const today = new Date();
  const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const theme = dayTheme(birth, iso);

  return (
    <main>
      <Link href="/" className="back">← 入口へ戻る</Link>

      <section className="you-hero">
        <div className="theme-label">あなたの基本設計図</div>
        <div className="profile-row">
          <div><span className="pv">{lp}</span><span className="pk">ライフパス(生まれ持った数)</span></div>
          <div><span className="pv">{sign.ja}</span><span className="pk">太陽星座{sign.boundary ? "(境界日)" : ""}</span></div>
        </div>
        <p className="you-motto">{you.motto}</p>
        <p className="you-line">{previewLine(lp)}</p>
      </section>

      <section className="you-sec">
        <h2>本質</h2>
        <p>{you.essence}</p>
      </section>

      <section className="you-sec">
        <h2>潜在能力</h2>
        <p>{you.potential}</p>
      </section>

      <section className="you-sec">
        <h2>得意な傾向</h2>
        <dl className="tend">
          <div><dt>考え方</dt><dd>{you.think}</dd></div>
          <div><dt>行動</dt><dd>{you.act}</dd></div>
          <div><dt>人との関わり</dt><dd>{you.relate}</dd></div>
          <div><dt>仕事</dt><dd>{you.work}</dd></div>
        </dl>
      </section>

      <section className="you-sec">
        <h2>意識すると伸びるポイント</h2>
        <p>{you.growth}</p>
      </section>

      {fortune ? (
        <FortuneFlow fortune={fortune} birth={birth} />
      ) : (
        <section className="you-sec today">
          <div className="theme-label">今日のあなた</div>
          <div className="theme-word">{theme.word}</div>
          <p className="theme-line">{theme.line}</p>
        </section>
      )}

      <section className="you-next">
        <p>次は、今日のレースで<br />あなたとの相性を見てみましょう。</p>
        <Link href="/races" className="cta">今日のレースを見る</Link>
      </section>

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果や未来を保証するものではありません。
        <br />
        開発版: プロフィール文はMockです(正式実装では知識ベースから生成します)。
      </footer>
    </main>
  );
}
