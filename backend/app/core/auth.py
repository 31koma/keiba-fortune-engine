"""単一ユーザーのログイン認証。

方針:
- **平文パスワードは保存しない。** PBKDF2-HMAC-SHA256(600,000回)のハッシュのみを .env に置く。
  ハッシュ生成は「パスワード設定.command」がローカルで行うため、平文がリポジトリにも
  ログにも残らない。
- セッションはHMAC-SHA256で署名したCookie。サーバ側にセッション表を持たないので
  再起動しても壊れないが、失効させたいときは KEIBA_AUTH_SECRET を変えれば全無効化できる。
- 標準ライブラリのみ(新しい依存を増やさない)。
- **fail closed**: 認証が必要な設定なのにハッシュ未設定なら、開放せず503で止める。

これはアプリを外部公開したときの入口の鍵であり、占術ロジックとは無関係。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

ALGO = "pbkdf2_sha256"
ITERATIONS = 600_000
COOKIE_NAME = "hoshiyomi_session"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# --- パスワード ---------------------------------------------------------

def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """保存用の文字列を作る。形式: pbkdf2_sha256$回数$salt$hash"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGO}${iterations}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    """タイミング攻撃を避けて比較する。形式不正は静かにFalse。"""
    try:
        algo, iters, salt_b64, dk_b64 = stored.split("$")
        if algo != ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 _b64d(salt_b64), int(iters))
        return hmac.compare_digest(dk, _b64d(dk_b64))
    except Exception:  # noqa: BLE001 (壊れた設定でも例外を漏らさない)
        return False


# --- セッション ---------------------------------------------------------

def issue_session(subject: str, secret: str, ttl_seconds: int) -> str:
    """署名付きセッショントークン。中身は subject と失効時刻だけ(秘密は入れない)。"""
    exp = int(time.time()) + ttl_seconds
    payload = f"{subject}|{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return f"{_b64e(payload)}.{_b64e(sig)}"


def read_session(token: str, secret: str) -> str | None:
    """有効ならsubject(メールアドレス)を返す。改ざん・期限切れはNone。"""
    if not token or not secret:
        return None
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = _b64d(payload_b64)
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            return None
        subject, exp = payload.decode("utf-8").rsplit("|", 1)
        if int(exp) < int(time.time()):
            return None
        return subject
    except Exception:  # noqa: BLE001
        return None


# --- 総当たり対策 -------------------------------------------------------

class LoginThrottle:
    """IPごとの失敗回数でロックする簡易スロットル(プロセス内メモリ)。

    外部公開時の最低限の歯止め。厳密な分散対策ではないが、単一プロセス運用の
    このアプリでは十分に効く。再起動でリセットされる点は許容。
    """

    def __init__(self, max_failures: int = 8, lock_seconds: int = 900,
                 window_seconds: int = 900):
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self.window_seconds = window_seconds
        self._state: dict[str, tuple[int, float, float]] = {}  # ip -> (回数, 初回, 解除時刻)

    def locked_for(self, ip: str) -> int:
        """ロック中なら残り秒数、そうでなければ0。"""
        rec = self._state.get(ip)
        if not rec:
            return 0
        _, _, until = rec
        remain = int(until - time.time())
        return remain if remain > 0 else 0

    def record_failure(self, ip: str) -> None:
        now = time.time()
        count, first, until = self._state.get(ip, (0, now, 0.0))
        if now - first > self.window_seconds and until <= now:
            count, first = 0, now  # 古い失敗は時効
        count += 1
        if count >= self.max_failures:
            until = now + self.lock_seconds
            count, first = 0, now
        self._state[ip] = (count, first, until)

    def record_success(self, ip: str) -> None:
        self._state.pop(ip, None)
