"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Orbit from "./components/Orbit";
import BirthdateModal from "./components/BirthdateModal";

export default function Home() {
  const [modal, setModal] = useState(false);
  const [birth, setBirth] = useState<string | null>(null);
  useEffect(() => { setBirth(localStorage.getItem("birthdate")); }, []);

  return (
    <main>
      <section className="hero">
        <div className="brand-en">Hoshiyomi Turf</div>
        <h1 className="brand">星読みターフ <small>(仮称)</small></h1>
        <p className="catch">星と数字で、<em>レースを読む。</em></p>
        <p className="lede">
          その馬の生まれ日。騎手の数字。今日の星回り。そして、あなた。
        </p>
      </section>

      <div className="orbit-wrap">
        <Orbit userActive={!!birth} />
      </div>
      <p className="orbit-caption">
        4つの生まれ日が交わる一点に、あなただけのレースの物語が生まれます。
      </p>

      <Link href="/races" className="cta">今日のレースを見る</Link>
      <button className={`cta-sub ${birth ? "registered" : ""}`} onClick={() => setModal(true)}>
        {birth ? `あなたの生年月日: ${birth}(変更する)` : "自分の生年月日を登録する"}
      </button>
      {!birth && <p className="cta-note">登録すると「あなた」の軌道が加わり、4者分析になります</p>}

      <section className="section">
        <h2>このアプリができること</h2>
        <p>
          数秘術と西洋占星術——2000年続く「読み」の伝統をレンズに、
          競走馬・騎手・レース日・あなたの4者の関係性を分析します。
          当てるためではなく、いつもの競馬をもっと深く味わうために。
        </p>
        <div className="terms">
          <span className="term"><b>ライフパス</b>(生まれ持った数)</span>
          <span className="term"><b>トライン</b>(120度・最も調和する角度)</span>
          <span className="term"><b>パーソナルデイ</b>(その馬にとっての今日)</span>
          <span className="term"><b>元素</b>(火・地・風・水の気質)</span>
        </div>
      </section>

      <section className="section">
        <h2>分析だけで終わらせない</h2>
        <div className="answer-box">
          <div className="label">今回の結論</div>
          <p>
            すべての鑑定は、参考にできる「今回の結論」で締めくくります。
            根拠(使ったルールと出典)もあわせて提示。
            そして最後にどう読むかは——あなたの楽しみです。
          </p>
        </div>
      </section>

      <footer>
        本鑑定は占術に基づくエンターテインメントであり、
        レース結果を予測・保証するものではありません。
        <br />
        的中・必勝をうたうサービスではなく、馬券の購入を推奨するものでもありません。
        <br />
        開発版 / Mockデータ表示中 / 知識ベース v1.2 準拠
      </footer>

      {modal && (
        <BirthdateModal
          onClose={() => setModal(false)}
          onSaved={(d) => { setBirth(d); setModal(false); }}
        />
      )}
    </main>
  );
}
