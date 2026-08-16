// 未ログインの画面アクセスを /login へ送る門番。
// ここではCookieが「在るか」しか見ない。中身の検証はバックエンドの責任
// (署名検証を一箇所に集めるため。Edge側で秘密鍵を持たない)。
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE = "hoshiyomi_session";

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  // ログイン画面とAPI中継は素通し(APIはバックエンドが401を返す)
  if (pathname === "/login" || pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  if (!req.cookies.get(COOKIE)) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    // ログイン後に元の画面へ戻すため、行き先を覚えておく
    url.search = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // 静的ファイルとfaviconは対象外
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|svg|ico|webp)$).*)"],
};
