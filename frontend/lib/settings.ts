// 鑑定設定(端末ローカル)。
// 「あなたの誕生日を鑑定に使用する」ON/OFF。OFFまたは未登録なら実効誕生日はnullとなり、
// バックエンドは user_birth なしの客観鑑定(without_user重み)へ自動的に切り替わる。
// 誕生日データ自体は消さない(いつでも戻せる)。

const KEY = "birthdate_enabled";

export function birthdateEnabled(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(KEY) !== "0";
}

export function setBirthdateEnabled(on: boolean) {
  localStorage.setItem(KEY, on ? "1" : "0");
}

/** 実効誕生日: 登録済みかつ設定ONのときのみ値を返す。それ以外はnull(=客観鑑定) */
export function effectiveBirth(birth: string | null, enabled: boolean): string | null {
  return enabled && birth ? birth : null;
}

// --- プレミアムモード(端末ローカルの仮フラグ。決済実装までの暫定) ---
// 星読みターフは複勝(3着以内)重視のため、通常モードの着順表示は3着まで。
// 4着以下の詳細表示はプレミアム限定(localStorage "premium" = "1" で有効)。
const PREMIUM_KEY = "premium";

export function isPremium(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(PREMIUM_KEY) === "1";
}
