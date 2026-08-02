"use client";
// 画面上部の戻りナビ。「迷わず戻れる」を最優先に、
// トップへ戻る(固定)+前の画面へ戻る(文脈依存)の2段構成。
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function PageNav({ onBack }: {
  /** ドリルダウン内の「一つ前」。未指定ならブラウザ履歴を戻る */
  onBack?: () => void;
}) {
  const router = useRouter();
  return (
    <nav className="page-nav" aria-label="ページ移動">
      <Link href="/" className="nav-link">← トップへ戻る</Link>
      <button type="button" className="nav-link"
        onClick={() => (onBack ? onBack() : router.back())}>
        ← 前の画面へ戻る
      </button>
    </nav>
  );
}
