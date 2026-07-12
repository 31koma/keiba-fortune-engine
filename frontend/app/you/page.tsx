"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import BirthdateModal from "../components/BirthdateModal";
import { dayTheme, lifePath, previewLine, sunSign } from "@/lib/preview";
import { YOU } from "@/lib/you";

export default function You() {
  const [birth, setBirth] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [modal, setModal] = useState(false);
  useEffect(() => {
    setBirth(localStorage.getItem("birthdate"));
    setReady(true);
  }, []);

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

      <section className="you-sec today">
        <div className="theme-label">今日のあなた</div>
        <div className="theme-word">{theme.word}</div>
        <p className="theme-line">{theme.line}</p>
      </section>

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
