"use client";
// 画面右上の小さなログアウト。ログイン画面では出さない。
import { usePathname, useRouter } from "next/navigation";
import { API_BASE } from "../../lib/api";

export default function LogoutButton() {
  const pathname = usePathname();
  const router = useRouter();
  if (pathname === "/login") return null;

  async function logout() {
    try {
      await fetch(`${API_BASE}/v1/auth/logout`, {
        method: "POST", credentials: "same-origin",
      });
    } catch {
      // 通信できなくてもCookieは下で消えるので、そのまま進める
    }
    document.cookie = "hoshiyomi_session=; Max-Age=0; path=/";
    router.replace("/login");
    router.refresh();
  }

  return (
    <>
      <button type="button" onClick={logout} className="logout-btn"
        aria-label="ログアウト">ログアウト</button>
      <style>{`
        .logout-btn {
          position: fixed; top: 10px; right: 12px; z-index: 50;
          background: rgba(0,0,0,0.28); border: 1px solid rgba(255,255,255,0.14);
          color: rgba(238,241,248,0.72); border-radius: 999px;
          padding: 5px 12px; font-size: 11px; letter-spacing: .06em; cursor: pointer;
        }
        .logout-btn:hover { color: #eef1f8; border-color: rgba(255,255,255,0.3); }
      `}</style>
    </>
  );
}
