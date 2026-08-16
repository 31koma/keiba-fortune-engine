/** @type {import('next').NextConfig} */

// バックエンド(FastAPI)の実体。デプロイ先では BACKEND_ORIGIN で差し替える。
// 注意: rewritesの行き先は**ビルド時に焼き込まれる**(.next/routes-manifest.json)。
// 公開時は `BACKEND_ORIGIN=... npm run build` の順で、buildの前に環境変数を渡すこと。
// startの時だけ渡しても効かない(検証済み・2026-08-14)。
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // PWA対応はPhase 4で導入予定(manifest/service worker)。

  // 画面とAPIを同一オリジンに揃えるための中継。
  // こうしておくとログインCookieが素直に効き、CORSも不要になる
  // (ネット公開時にフロントとAPIでドメインが割れる事故を防ぐ)。
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_ORIGIN}/:path*` }];
  },
};
export default nextConfig;
