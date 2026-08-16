"use client";
// ログイン画面。星読みターフの入口。
// パスワードはこの画面から出た後、平文としてはどこにも保存されない。
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API_BASE } from "../../lib/api";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email, password }),
      });
      if (r.ok) {
        router.replace(next);
        router.refresh();
        return;
      }
      const body = await r.json().catch(() => null);
      setError(body?.detail?.detail ?? "ログインできませんでした。");
    } catch {
      setError("サーバーに繋がりませんでした。起動しているか確認してください。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-wrap">
      <div className="login-card">
        <p className="login-mark">✦</p>
        <h1 className="login-title">星読みターフ</h1>
        <p className="login-sub">星と数字で、レースを読む。</p>

        <form onSubmit={onSubmit} className="login-form">
          <label className="login-label" htmlFor="email">メールアドレス</label>
          <input id="email" type="email" autoComplete="username" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            className="login-input" inputMode="email" />

          <label className="login-label" htmlFor="password">パスワード</label>
          <input id="password" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)}
            className="login-input" />

          {error && <p className="login-error" role="alert">{error}</p>}

          <button type="submit" className="login-button" disabled={busy}>
            {busy ? "確認しています…" : "扉をひらく"}
          </button>
        </form>
      </div>

      <style>{`
        .login-wrap {
          min-height: 100dvh; display: grid; place-items: center;
          padding: 24px; background: #131a30; color: #eef1f8;
        }
        .login-card {
          width: 100%; max-width: 380px; text-align: center;
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10);
          border-radius: 18px; padding: 36px 26px 30px;
        }
        .login-mark { font-size: 26px; margin: 0 0 10px; color: #f2c66d; }
        .login-title { font-size: 22px; letter-spacing: .14em; margin: 0 0 6px; font-weight: 600; }
        .login-sub { font-size: 12.5px; opacity: .62; margin: 0 0 26px; letter-spacing: .06em; }
        .login-form { display: flex; flex-direction: column; text-align: left; }
        .login-label { font-size: 11.5px; opacity: .66; margin-bottom: 6px; letter-spacing: .08em; }
        .login-input {
          background: rgba(0,0,0,0.28); border: 1px solid rgba(255,255,255,0.16);
          border-radius: 10px; padding: 12px 13px; color: #eef1f8;
          font-size: 16px; margin-bottom: 16px; width: 100%; box-sizing: border-box;
        }
        .login-input:focus { outline: none; border-color: #f2c66d; }
        .login-button {
          margin-top: 8px; padding: 13px; border-radius: 10px; border: none;
          background: #f2c66d; color: #1b2038; font-size: 15px; font-weight: 600;
          letter-spacing: .08em; cursor: pointer;
        }
        .login-button:disabled { opacity: .55; cursor: default; }
        .login-error {
          color: #ffb4a8; font-size: 12.5px; margin: 2px 0 10px; line-height: 1.6;
        }
      `}</style>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
