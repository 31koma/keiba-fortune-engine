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
    """ZZ9.9等。空白・0は未設定としてNone(オッズ0.0は存在しない)。"""
    try:
        v = float(s.strip())
    except ValueError:
        return None
    return v if v > 0 else None


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
