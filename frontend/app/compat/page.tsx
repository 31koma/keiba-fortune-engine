"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import BirthdateModal from "../components/BirthdateModal";
import { lifePath, sunSign } from "@/lib/preview";
import { compatReading, RELATION_TYPES } from "@/lib/compat";

export default function Compat() {
  const [birth, setBirth] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [modal, setModal] = useState(false);
  const [name, setName] = useState("");
  const [y, setY] = useState<number | "">("");
  const [m, setM] = useState<number | "">("");
  const [d, setD] = useState<number | "">("");
  const [relation, setRelation] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null); // 相手ISO(保存しない)

  useEffect(() => { setBirth(localStorage.getItem("birthdate")); setReady(true); }, []);

  const days = useMemo(() => (y === "" || m === "") ? 31
    : new Date(Number(y), Number(m), 0).getDate(), [y, m]); // 閏年対応
  const now = new Date().getFullYear();
  const years = Array.from({ length: 120 }, (_, i) => now - i);
  const iso = y !== "" && m !== "" && d !== ""
    ? `${y}-${String(m).padStart(2, "0")}-${String(Math.min(Number(d), days)).padStart(2, "0")}`
    : null;

  if (!ready) return <main />;

  if (!birth) {
    return (
      <main>
        <Link href="/" className="back">← 入口へ戻る</Link>
        <section className="you-invite">
          <div className="theme-label">相性をみる</div>
          <p className="races-q">まず、あなたの生まれ日から。</p>
          <p className="races-sub">相性はふたりの生まれ日から読みます。最初にあなたの登録をどうぞ。</p>
          <button className="cta" onClick={() => setModal(true)}>生年月日を登録する</button>
        </section>
        {modal && <BirthdateModal onClose={() => setModal(false)}
          onSaved={(v) => { setBirth(v); setModal(false); }} />}
      </main>
    );
  }

  if (result) {
    const r = compatReading(birth, result);
    const other = name.trim() || "相手";
    return (
      <main>
        <button className="back link-btn" onClick={() => setResult(null)}>← 入力に戻る</button>

        <section className="you-hero">
          <div className="theme-label">相性をみる</div>
          <div className="pair-row">
            <div className="pair-cell">
              <div className="pair-name">あなた</div>
              <div className="pv">{lifePath(birth)}</div>
              <div className="pk">{sunSign(birth).ja}</div>
            </div>
            <div className="pair-x">×</div>
            <div className="pair-cell">
              <div className="pair-name">{other}</div>
              <div className="pv">{lifePath(result)}</div>
              <div className="pk">{sunSign(result).ja}</div>
            </div>
          </div>
        </section>

        <section className="you-sec today">
          <div className="theme-label">今回の結論</div>
          <p className="conclusion">{r.conclusion}</p>
          <div className="stars">{"★".repeat(r.stars)}{"☆".repeat(5 - r.stars)}</div>
          <p className="stars-note">星は暫定表示(Mock)です。正式なスコアは検証後に導入します。</p>
        </section>

        <section className="you-sec blueprint">
          <h2>関係性の設計図</h2>
          <div className="theme-label" style={{ marginTop: 18 }}>共通テーマ</div>
          <div className="theme-word">{r.theme.word}</div>
          <p className="theme-line">{r.theme.line}</p>
        </section>

        <section className="you-sec"><h2>惹かれやすい理由</h2><p>{r.attract}</p></section>
        <section className="you-sec"><h2>価値観の共通点</h2><p>{r.common}</p></section>
        <section className="you-sec"><h2>違いが生まれやすいところ</h2><p>{r.diff}</p></section>
        <section className="you-sec"><h2>この関係を育てるヒント</h2><p>{r.hint}</p></section>

        <section className="you-sec">
          <h2>相性キーワード</h2>
          <div className="terms" style={{ marginTop: 18 }}>
            {r.keywords.map((k) => <span className="term" key={k}><b>{k}</b></span>)}
          </div>
        </section>

        <section className="you-next">
          <p className="hint-line">この関係をより良くする一言 —<br />「{r.oneWord}」</p>
          <button className="cta-sub" onClick={() => { setResult(null); setName(""); setY(""); setM(""); setD(""); }}>
            別の人との相性をみる
          </button>
          <div className="home-links">
            <Link href="/you">あなたの基本設計図へ</Link>
            <Link href="/races">今日のレースを見る</Link>
          </div>
        </section>

        <footer>
          本鑑定は占術に基づくエンターテインメントであり、
          関係の成否を断定・保証するものではありません。
          <br />開発版: 相性結果はMockデータです。入力内容は外部送信されず、相手の情報は保存されません。
        </footer>
      </main>
    );
  }

  return (
    <main>
      <Link href="/" className="back">← 入口へ戻る</Link>
      <section className="races-lead">
        <p className="races-q">相性をみる</p>
        <p className="races-sub">
          ふたりの「関係性の設計図」を読み解きます。恋人、家族、友人、仕事仲間 —
          すべての人間関係が対象です。
        </p>
      </section>

      <section className="compat-form">
        <label className="form-label">相手の名前(ニックネーム可)</label>
        <input className="text-input" value={name} maxLength={20}
          onChange={(e) => setName(e.target.value)} placeholder="例: ○○さん" />

        <label className="form-label">相手の生年月日</label>
        <div className="date-row">
          <select value={y} onChange={(e) => setY(Number(e.target.value))} aria-label="年">
            <option value="" disabled>年</option>
            {years.map((v) => <option key={v} value={v}>{v}年</option>)}
          </select>
          <select value={m} onChange={(e) => setM(Number(e.target.value))} aria-label="月">
            <option value="" disabled>月</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((v) => <option key={v} value={v}>{v}月</option>)}
          </select>
          <select value={d} onChange={(e) => setD(Number(e.target.value))} aria-label="日">
            <option value="" disabled>日</option>
            {Array.from({ length: days }, (_, i) => i + 1).map((v) => <option key={v} value={v}>{v}日</option>)}
          </select>
        </div>

        <label className="form-label">関係(任意。将来、読み方が少し変わります)</label>
        <div className="relation-row">
          {RELATION_TYPES.map((t) => (
            <button key={t} className={`term relation ${relation === t ? "on" : ""}`}
              onClick={() => setRelation(relation === t ? null : t)}>{t}</button>
          ))}
        </div>

        <button className="cta" disabled={!iso} style={{ marginTop: 30 }}
          onClick={() => setResult(iso)}>
          ふたりの設計図を読む
        </button>
        <p className="cta-note">入力内容は外部送信されません。相手の情報は保存されません。</p>
      </section>

      <footer>本鑑定は占術に基づくエンターテインメントです(開発版・Mock)。</footer>
    </main>
  );
}
