"use client";
import { useMemo, useState } from "react";
import { lifePath, previewLine, sunSign } from "@/lib/preview";

/** 生年月日の登録モーダル。
 *  直打ちなし: 年月日とも<select>(iPhoneではOS標準ホイール、PCではプルダウン)。 */
export default function BirthdateModal({
  onClose, onSaved,
}: { onClose: () => void; onSaved: (d: string) => void }) {
  const now = new Date().getFullYear();
  const years = Array.from({ length: 120 }, (_, i) => now - i); // 120年前まで
  const [y, setY] = useState<number | "">("");
  const [m, setM] = useState<number | "">("");
  const [d, setD] = useState<number | "">("");
  const [saved, setSaved] = useState<string | null>(null);

  const days = useMemo(() => {
    if (y === "" || m === "") return 31;
    return new Date(Number(y), Number(m), 0).getDate(); // 閏年対応
  }, [y, m]);

  const iso = y !== "" && m !== "" && d !== ""
    ? `${y}-${String(m).padStart(2, "0")}-${String(Math.min(Number(d), days)).padStart(2, "0")}`
    : null;

  if (saved) {
    const lp = lifePath(saved);
    const sign = sunSign(saved);
    return (
      <div className="modal-bg" onClick={() => { onSaved(saved); }}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="reveal">
            <div className="label">あなたの基本設計図</div>
            <div className="profile-row">
              <div><span className="pv">{lp}</span><span className="pk">ライフパス</span></div>
              <div><span className="pv">{sign.ja}</span><span className="pk">太陽星座{sign.boundary ? "(境界日)" : ""}</span></div>
            </div>
            <p className="profile-line">「{previewLine(lp)}」</p>
            <p className="profile-note">
              これで4者分析の準備が整いました。レースを選ぶと、
              馬・騎手・その日との関係性が読めるようになります。
            </p>
            <button className="cta" onClick={() => onSaved(saved)}>
              軌道に加わる
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>あなたの生年月日</h3>
        <p>
          あなたもこのレースの参加者です。生年月日ひとつで、
          ライフパス(生まれ持った数)と太陽星座が定まります。
          <br />※開発版: この端末にのみ保存され、送信されません。
        </p>
        <div className="date-row">
          <select value={y} onChange={(e) => setY(Number(e.target.value))} aria-label="年">
            <option value="" disabled>年</option>
            {years.map((v) => <option key={v} value={v}>{v}年</option>)}
          </select>
          <select value={m} onChange={(e) => setM(Number(e.target.value))} aria-label="月">
            <option value="" disabled>月</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((v) => (
              <option key={v} value={v}>{v}月</option>
            ))}
          </select>
          <select value={d} onChange={(e) => setD(Number(e.target.value))} aria-label="日">
            <option value="" disabled>日</option>
            {Array.from({ length: days }, (_, i) => i + 1).map((v) => (
              <option key={v} value={v}>{v}日</option>
            ))}
          </select>
        </div>
        <div className="row">
          <button className="cta-sub" onClick={onClose}>あとで</button>
          <button className="cta" style={{ marginTop: 0 }} disabled={!iso}
            onClick={() => { localStorage.setItem("birthdate", iso!); setSaved(iso!); }}>
            登録する
          </button>
        </div>
      </div>
    </div>
  );
}
