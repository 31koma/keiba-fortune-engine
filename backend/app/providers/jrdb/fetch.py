"""JRDB会員データのダウンロードワーカー(骨格)。

- 認証: JRDB会員ID/パスワード(HTTP Basic)。.envの KEIBA_JRDB_USER /
  KEIBA_JRDB_PASSWORD から読む。コミット禁止
- 取得先URLは会員ページの案内に従い KEIBA_JRDB_BASE_URL で設定する
  (例: http://www.jrdb.com/member/data — 会員登録後に正確なパスを確認すること)
- 圧縮形式: .lzh(全種)/ .zip(KYI等、順次追加)。zipは標準ライブラリで展開。
  lzhは `lhafile` パッケージがあれば展開、なければ .lzh のまま保存して警告
- レース当日08:00-19:00は当日データ以外のアクセス制限あり(JRDB運用ルール)。
  過去データの一括取得は週明けに行うこと
"""
import io
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.providers.jrdb.spec import FILE_KINDS


class JRDBFetchError(RuntimeError):
    pass


# 確認済みのURLパターン(2026-07-16): {base}/{ディレクトリ}/{種別}{yymmdd}.lzh
# 例: http://www.jrdb.com/member/data/Bac/BAC260712.lzh(疎通確認済み)
_BASE_CANDIDATES = (
    "http://www.jrdb.com/member/data",
    "http://www2.jrdb.com/member/data",
)

# 種別→ディレクトリ名(既定は先頭大文字化)。騎手・調教師は仕様書と同じKs/Cs配下
_DIR_OVERRIDES = {"KZA": "Ks", "KSA": "Ks", "CZA": "Cs", "CSA": "Cs"}


def _dir_candidates(kind: str) -> list[str]:
    default = kind.capitalize()
    if kind in _DIR_OVERRIDES:
        return [_DIR_OVERRIDES[kind], default]
    return [default]


def _auth_header() -> str:
    if not (settings.jrdb_user and settings.jrdb_password):
        raise JRDBFetchError(
            "JRDB認証情報が未設定です(.envに KEIBA_JRDB_USER / KEIBA_JRDB_PASSWORD)")
    import base64
    token = base64.b64encode(
        f"{settings.jrdb_user}:{settings.jrdb_password}".encode()).decode()
    return f"Basic {token}"


def _get(url: str) -> bytes:
    """プリエンプティブBasic認証でGET(JRDBは401チャレンジを返さない場合がある)。"""
    req = urllib.request.Request(url, headers={
        "Authorization": _auth_header(), "User-Agent": "keiba-fortune-engine/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _extract(payload: bytes, filename: str, out_dir: Path) -> list[Path]:
    """zip/lzhを展開して.txtを保存。展開不能ならそのまま保存。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    if filename.endswith(".zip"):
        saved = []
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            for name in zf.namelist():
                p = out_dir / Path(name).name
                p.write_bytes(zf.read(name))
                saved.append(p)
        return saved
    if filename.endswith(".lzh"):
        try:
            import lhafile  # type: ignore  # 任意依存(pip install lhafile)
        except ImportError:
            p = out_dir / filename
            p.write_bytes(payload)
            print(f"警告: lhafile未導入のため展開せず保存: {p}")
            return [p]
        lf = lhafile.Lhafile(io.BytesIO(payload))
        saved = []
        for info in lf.infolist():
            p = out_dir / Path(info.filename).name
            p.write_bytes(lf.read(info.filename))
            saved.append(p)
        return saved
    p = out_dir / filename
    p.write_bytes(payload)
    return [p]


def fetch_day(target: date, kinds: tuple[str, ...] = FILE_KINDS,
              out_dir: Path | None = None) -> list[Path]:
    """対象日のデータ一式を取得・展開する。存在しない種別はスキップ。"""
    out = Path(out_dir or settings.jrdb_data_dir)
    ymd = target.strftime("%y%m%d")
    bases = [settings.jrdb_base_url] + [b for b in _BASE_CANDIDATES
                                        if b != settings.jrdb_base_url]
    saved: list[Path] = []
    for kind in kinds:
        got = False
        last_err = ""
        for base in bases:
            for subdir in _dir_candidates(kind):
                for ext in (".zip", ".lzh"):
                    url = f"{base}/{subdir}/{kind}{ymd}{ext}"
                    try:
                        saved += _extract(_get(url), f"{kind}{ymd}{ext}", out)
                        print(f"取得: {url}")
                        got = True
                        break
                    except urllib.error.HTTPError as e:
                        last_err = f"HTTP {e.code}: {url}"
                        if e.code in (401, 403, 404):
                            continue  # 認証/未配布/パス違いは次候補へ
                        raise JRDBFetchError(f"{url}: HTTP {e.code}") from e
                if got:
                    break
            if got:
                break
        if not got:
            print(f"注意: {kind}{ymd} 取得不可({last_err or '未配布かパス要確認'})")
    return saved


if __name__ == "__main__":
    import sys
    d = (date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today())
    for p in fetch_day(d):
        print(p)
