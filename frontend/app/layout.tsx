import type { Metadata, Viewport } from "next";
import "./globals.css";
import { MOCK_NOTICE } from "@/lib/mock";

export const metadata: Metadata = {
  title: "星読みターフ(仮称) — 星と数字で、レースを読む。",
  description:
    "競走馬・騎手・レース日・あなた。4つの生まれ日の関係性を数秘術と西洋占星術で読む、競馬観戦エンターテインメント。結果を予測・保証するものではありません。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#131a30",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <div className="dev-badge">
          <b>DEV</b> {MOCK_NOTICE}・実レースデータ未接続
        </div>
        {children}
      </body>
    </html>
  );
}
