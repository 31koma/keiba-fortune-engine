"""JRDB固定長レコードのパーサ。spec.pyのレイアウト定義(データ)に従って切り出す。

- cp932でバイト単位スライス(全角混在のため文字数ではなくバイト位置)
- TYPE Z(0のとき空白)/ ZZ9.9(小数)/ F(16進1桁)に対応
- 解釈・意味づけは一切行わない(値の取り出しのみ)
"""
from datetime import date

from app.providers.jrdb.spec import LAYOUTS

# 位置が意味を持つ繰り返しフィールド(strip禁止)
_NO_STRIP = {"win_odds", "place_odds"}


def slice_field(record: bytes, start: int, length: int, strip: bool = True) -> str:
    """1始まりバイト位置で切り出し、cp932でデコードする。"""
    raw = record[start - 1: start - 1 + length]
    text = raw.decode("cp932", errors="replace")
    return text.strip() if strip else text


def to_int(s: str) -> int | None:
    s = s.strip()
    return int(s) if s and s.lstrip("-").isdigit() else None


def to_float(s: str) -> float | None:
    """オッズ用。空白・0は未設定としてNone(オッズ0.0は存在しない)。

    負値・0を落とすため、**指数系フィールドには使わないこと**(to_index_float を使う)。
    """
    try:
        v = float(s.strip())
    except ValueError:
        return None
    return v if v > 0 else None


def to_index_float(s: str) -> float | None:
    """指数系(IDM・騎手・情報・総合・調教・厩舎)用。0と負値を値として保持する。

    JRDBの調教指数・厩舎指数・情報指数は負値をとり、騎手指数は0.0をとる。
    これらを to_float() に通すと未設定扱いで消える(2026-08-15 run11で判明。
    KYI260815では調教指数259/487・厩舎指数236/487・情報指数243/487が欠落し、
    「合」の物理平均が一部の馬で理・騎の2項だけで計算されていた)。
    未設定は空白で表現されるため、空白・非数値のみ None とする。
    """
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_date(s: str) -> date | None:
    s = s.strip()
    if len(s) != 8 or not s.isdigit() or s == "00000000":
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def hex_digit(s: str) -> int | None:
    """レースキー「日」は16進1桁(1-9,A-F)。"""
    try:
        return int(s.strip(), 16)
    except ValueError:
        return None


def parse_records(data: bytes, kind: str) -> list[dict]:
    """ファイル全体をレコード長で分割し、定義済みフィールドを辞書化する。"""
    layout = LAYOUTS[kind]
    rec_len = layout["record_len"]
    out: list[dict] = []
    # 末尾の改行有無など配布ゆらぎに耐えるため、行分割ではなく長さで切る
    pos = 0
    while pos + rec_len <= len(data):
        rec = data[pos:pos + rec_len]
        pos += rec_len
        if not rec.strip():
            continue
        out.append({
            name: slice_field(rec, st, ln, strip=name not in _NO_STRIP)
            for name, (st, ln) in layout["fields"].items()
        })
    return out


def parse_win_odds(odds_field: str, head_count: int) -> dict[int, float | None]:
    """OZの単勝オッズ(5バイト×18頭・馬番順、strip前の生文字列)を{馬番: オッズ}へ。"""
    item = LAYOUTS["OZ"]["odds_item_len"]
    result: dict[int, float | None] = {}
    for i in range(min(head_count, LAYOUTS["OZ"]["odds_count"])):
        result[i + 1] = to_float(odds_field[i * item:(i + 1) * item])
    return result


def parse_payouts(data: bytes) -> dict[str, dict]:
    """HJC(払戻情報)をレースキー→式別→[(組番, 払戻金), ...] へ畳む。

    JRDBは確定複勝配当・ワイド・三連複などの配当をSEDには入れないため、
    回収率の検証にはこのファイルが要る(2026-08-16に導入)。
    組番が全0のスロットは「該当なし」なので落とす。払戻金の単位は円(100円あたり)。
    """
    layout = LAYOUTS["HJC"]
    rec_len = layout["record_len"]
    out: dict[str, dict] = {}
    pos = 0
    while pos + rec_len <= len(data):
        rec = data[pos:pos + rec_len]
        pos += rec_len
        if not rec.strip():
            continue
        key = slice_field(rec, 1, 8)
        race: dict[str, list[tuple[str, int]]] = {}
        for name, start, combo_len, pay_len, count in layout["payouts"]:
            p = start
            items: list[tuple[str, int]] = []
            for _ in range(count):
                combo = slice_field(rec, p, combo_len)
                pay = to_int(slice_field(rec, p + combo_len, pay_len))
                p += combo_len + pay_len
                if combo and set(combo) != {"0"}:
                    items.append((combo, pay or 0))
            race[name] = items
        out[key] = race
    return out


def combo_set(combo: str) -> frozenset[int]:
    """組番文字列(例 '031014')を馬番の集合へ。順序のある式別には使わないこと。"""
    return frozenset(int(combo[i:i + 2]) for i in range(0, len(combo), 2))
