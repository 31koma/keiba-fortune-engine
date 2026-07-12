"use client";
import { useState } from "react";

export default function BirthdateModal({
  onClose, onSaved,
}: { onClose: () => void; onSaved: (d: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>あなたの生年月日</h3>
        <p>
          あなたもこのレースの参加者です。生年月日ひとつで、馬・騎手・レース日との
          関係性(ライフパス=生まれ持った数、星座の角度)を読む準備が整います。
          <br />
          ※開発版: この端末にのみ保存され、送信されません。
        </p>
        <input type="date" value={value} onChange={(e) => setValue(e.target.value)}
          aria-label="生年月日" />
        <div className="row">
          <button className="cta-sub" onClick={onClose}>あとで</button>
          <button className="cta" style={{ marginTop: 0 }} disabled={!value}
            onClick={() => { localStorage.setItem("birthdate", value); onSaved(value); }}>
            登録する
          </button>
        </div>
      </div>
    </div>
  );
}
