"""JRDBDataProvider: JRDBの固定長ファイル(ローカルのデータディレクトリ)→共通DTO。

- データ取得は fetch.py(会員認証ダウンロード)または手動配置。本アダプタは
  data_dir 内の展開済み .txt を読むだけ(ネットワークアクセスしない)
- オッズについて: OZ/KYIの「基準オッズ」はJRDB算出の想定オッズ(専門紙の印由来)
  であり、市場の実売オッズではない。集合意識係数としては
  「専門家の集合意識の近似」にあたる。発走直前の実売オッズ(大衆の集合意識)は
  TYB(直前データ)で将来対応する
- 正規のデータ提供サービスであり horse_data_policy(スクレイピング禁止)に適合。
  個人利用契約のため、エンドユーザーへの再配信にはJRA商用契約が別途必要
"""
from datetime import date, datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.domain.dto import HorseDTO, JockeyDTO, RaceDTO, RaceEntryDTO
from app.providers.base import DataProviderSet, register_provider
from app.providers.jrdb import parser
from app.providers.jrdb.spec import (COURSE_CODES, GRADE_CODES, SEX_CODES,
                                     TRACK_CODES)


def _yymmdd(d: date) -> str:
    return d.strftime("%y%m%d")


@register_provider("jrdb")
class JRDBDataProvider(DataProviderSet):
    """data_dir に置かれた JRDB ファイル群(BAC/KYI/UKC/KZA/OZ)を読む。"""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or settings.jrdb_data_dir)
        self._horses: dict[str, HorseDTO] = {}
        self._jockeys: dict[str, JockeyDTO] = {}
        self._races: dict[str, RaceDTO] = {}
        self._positions: dict[str, list[tuple[str, int]]] = {}  # 血統番号→[(ymd,着順)]
        self._loaded_masters = False
        self._loaded_results = False
        self._loaded_days: set[str] = set()

    # ---------- ファイル読込 ----------
    def _read(self, kind: str, ymd: str | None = None) -> list[dict]:
        """種別+日付のファイルを読む。日付なし(マスタ)は全ファイルを古い順に
        連結して返す(呼び出し側で新しい方が上書き)。開催日をまたいでも
        過去出走馬・騎手が消えないようにするため。"""
        if ymd:
            path = self.data_dir / f"{kind}{ymd}.txt"
            if not path.is_file():
                return []
            return parser.parse_records(path.read_bytes(), kind)
        rows: list[dict] = []
        for path in sorted(self.data_dir.glob(f"{kind}[0-9]*.txt")):
            rows += parser.parse_records(path.read_bytes(), kind)
        return rows

    def _load_masters(self) -> None:
        """馬(UKC)・騎手(KZA)マスタ。生年月日の正本はJRDB配布データ。"""
        if self._loaded_masters:
            return
        now = datetime.now(timezone.utc)
        for row in self._read("UKC"):
            bd = parser.to_date(row["birth_date"])
            if not row["pedigree_id"] or bd is None:
                continue  # 生年月日欠損は登録しない(補完しない)
            self._horses[row["pedigree_id"]] = HorseDTO(
                internal_id=row["pedigree_id"], provider_id=row["pedigree_id"],
                registered_name=row["horse_name"], official_english_name=None,
                birth_date=bd, sex=SEX_CODES.get(row["sex_code"]),
                sire=row["sire_name"] or None, dam=row["dam_name"] or None,
                source_provider="jrdb", retrieved_at=now)
        for row in self._read("KZA"):
            bd = parser.to_date(row["birth_date"])
            if not row["jockey_code"] or bd is None:
                continue
            self._jockeys[row["jockey_code"]] = JockeyDTO(
                internal_id=row["jockey_code"], provider_id=row["jockey_code"],
                name=row["jockey_name"], name_roman=None, birth_date=bd,
                source_provider="jrdb", retrieved_at=now)
        self._loaded_masters = True

    def _load_day(self, race_date: date) -> None:
        ymd = _yymmdd(race_date)
        if ymd in self._loaded_days:
            return
        self._loaded_days.add(ymd)
        self._load_masters()
        now = datetime.now(timezone.utc)

        # OZ: race_key → {馬番: 単勝基準オッズ}
        odds_by_race: dict[str, dict[int, float | None]] = {}
        for row in self._read("OZ", ymd):
            hc = parser.to_int(row["head_count"]) or 0
            odds_by_race[row["race_key"]] = parser.parse_win_odds(row["win_odds"], hc)

        # KYI: race_key → 出走馬リスト
        entries_by_race: dict[str, list[dict]] = {}
        for row in self._read("KYI", ymd):
            entries_by_race.setdefault(row["race_key"], []).append(row)

        # BAC: レース情報
        day_entries: list[RaceEntryDTO] = []  # 理(IDM)の日内換算用
        for row in self._read("BAC", ymd):
            key = row["race_key"]
            rd = parser.to_date(row["yyyymmdd"])
            if rd is None:
                continue
            odds = odds_by_race.get(key, {})
            entries: list[RaceEntryDTO] = []
            for e in sorted(entries_by_race.get(key, []),
                            key=lambda r: parser.to_int(r["post_number"]) or 0):
                post = parser.to_int(e["post_number"])
                win = odds.get(post) if post else None
                if win is None:  # OZ欠損時はKYIの基準オッズへフォールバック
                    win = parser.to_float(e["base_win_odds"])
                physical = {
                    # 指数系は to_index_float(0と負値を保持)。to_float はオッズ専用
                    "idm": parser.to_index_float(e.get("idm", "")),
                    "jockey_idx": parser.to_index_float(e.get("jockey_idx", "")),
                    "info_idx": parser.to_index_float(e.get("info_idx", "")),
                    "total_idx": parser.to_index_float(e.get("total_idx", "")),
                    "cyokyo_idx": parser.to_index_float(e.get("cyokyo_idx", "")),
                    "kyusha_idx": parser.to_index_float(e.get("kyusha_idx", "")),
                    "base_place_odds": parser.to_float(e.get("base_place_odds", "")),
                    # 後段でレース内順位(*_rank)と日内10点換算(*10)を付与
                    "idm_rank": None, "idm10": None,
                    "cyokyo_rank": None, "cyokyo10": None,
                    "joc_rank": None, "joc10": None,
                    # 前日基準人気帯と p表v4 のセル(後段で日単位に付与)
                    "pop_rank": parser.to_int(e.get("base_win_rank", "")),
                    "pop_band": None, "joc_split": None, "cyo_split": None,
                    "v4_cell": None, "p_v4": None,
                }
                # ── 2026-08-16 追加: KYIの未使用項目を素通しする。
                #    すべて発走前に判明する値。**「合」の式には一切入れていない**
                #    (印・看板・並び順は従来どおり。まずは見えるようにするだけ)。
                #    採用したくなったら事前登録を切ってから。
                physical.update({
                    # 展開: どこを走るつもりの馬か
                    "kyakushitsu": parser.to_int(e.get("kyakushitsu", "")),
                    "ten_idx": parser.to_index_float(e.get("ten_idx", "")),
                    "pace_idx": parser.to_index_float(e.get("pace_idx", "")),
                    "agari_idx": parser.to_index_float(e.get("agari_idx", "")),
                    "position_idx": parser.to_index_float(e.get("position_idx", "")),
                    "pace_forecast": e.get("pace_forecast", "").strip() or None,
                    "michinaka_rank": parser.to_int(e.get("michinaka_rank", "")),
                    "last3f_rank": parser.to_int(e.get("last3f_rank", "")),
                    "goal_rank": parser.to_int(e.get("goal_rank", "")),
                    # 適性: 「合」がまだ見ていない距離と馬場
                    "kyori_tekisei": parser.to_int(e.get("kyori_tekisei", "")),
                    "shiba_tekisei": parser.to_int(e.get("shiba_tekisei", "")),
                    "dirt_tekisei": parser.to_int(e.get("dirt_tekisei", "")),
                    "omo_tekisei": parser.to_int(e.get("omo_tekisei", "")),
                    "rotation": parser.to_int(e.get("rotation", "")),
                    # 仕上がり・厩舎・騎手
                    "cyokyo_arrow": parser.to_int(e.get("cyokyo_arrow", "")),
                    "kyusha_hyoka": parser.to_int(e.get("kyusha_hyoka", "")),
                    "jockey_rentai": parser.to_index_float(e.get("jockey_rentai", "")),
                    # 一発の目
                    "gekiso_idx": parser.to_int(e.get("gekiso_idx", "")),
                    "ninki_idx": parser.to_int(e.get("ninki_idx", "")),
                    "blinker": (e.get("blinker", "").strip() or None),
                    "waku": parser.to_int(e.get("waku", "")),
                })
                entries.append(RaceEntryDTO(
                    horse_id=e["pedigree_id"], jockey_id=e["jockey_code"],
                    post_number=post, win_odds=win, physical=physical))
            # 物理指数のレース内順位(降順)。表示用であり占術スコアには使わない
            for fld, rkey in (("idm", "idm_rank"), ("cyokyo_idx", "cyokyo_rank"),
                              ("jockey_idx", "joc_rank")):
                ranked = sorted([en for en in entries
                                 if en.physical and en.physical[fld] is not None],
                                key=lambda en: -en.physical[fld])
                for i, en in enumerate(ranked):
                    en.physical[rkey] = i + 1
            day_entries.extend(entries)
            surface = TRACK_CODES.get(row["track_code"], "unknown")
            hhmm = row["start_hhmm"]
            start = f"{hhmm[:2]}:{hhmm[2:]}" if len(hhmm) == 4 and hhmm.isdigit() else None
            self._races[key] = RaceDTO(
                internal_id=key, provider_id=key, race_date=rd,
                racecourse=COURSE_CODES.get(key[:2], f"場{key[:2]}"),
                race_number=parser.to_int(key[6:8]) or 0, start_time=start,
                race_name=row["race_name"] or row["race_name_short"] or "レース",
                distance=parser.to_int(row["distance"]) or 0,
                surface=surface, race_class=GRADE_CODES.get(row["grade_code"]),
                entries=entries, source_provider="jrdb", retrieved_at=now)

        # 物理指数の日内10点換算: この日の最高=10.0・最低=0.0(小数1桁)。
        # 占術スコア(主/客/本/数/収)と同じ10点満点に揃える表示用スケール。
        # (調教指数など負値を持つ指数があるため、比率でなくmin-maxで統一する)
        for fld, key10 in (("idm", "idm10"), ("cyokyo_idx", "cyokyo10"),
                           ("jockey_idx", "joc10")):
            vals = [en.physical[fld] for en in day_entries
                    if en.physical and en.physical[fld] is not None]
            if not vals:
                continue
            lo, hi = min(vals), max(vals)
            span = hi - lo
            for en in day_entries:
                if en.physical and en.physical[fld] is not None and span > 0:
                    en.physical[key10] = round((en.physical[fld] - lo) / span * 10, 1)

        self._apply_p_table_v4(day_entries)

    # p表v4(2026-08-15発行)。11開催日プール n=5125(0711-0815)の実測複勝率。
    # 帯=前日基準人気(KYI 101,2)。分割=**その日・その人気帯の中での**騎手指数/調教指数
    # 中央値分割(降順の上位ceil(n/2)=high)。
    # レース内順位での分割は人気とほぼ同義になり効果が消えることを実測済みのため、
    # 必ず「日 × 人気帯」で切ること(定義を変えるとこの表は使えない)。
    # 日別の再現性: 騎↑調↑が帯ベースラインを上回った開催日は 1-3:11/11 / 4-6:9/11 / 7+:11/11。
    P_TABLE_V4: dict[str, dict[str, float]] = {
        "1-3": {"high/high": 0.624, "high/low": 0.530,
                "low/high": 0.481, "low/low": 0.404},
        "4-6": {"high/high": 0.347, "high/low": 0.262,
                "low/high": 0.244, "low/low": 0.192},
        "7+":  {"high/high": 0.163, "high/low": 0.072,
                "low/high": 0.099, "low/low": 0.033},
    }

    @classmethod
    def _apply_p_table_v4(cls, day_entries: list[RaceEntryDTO]) -> None:
        """その日の全出走馬に 人気帯 × 騎調セル と 複勝率p(v4)を付与する。"""
        for en in day_entries:
            if not en.physical:
                continue
            rank = en.physical.get("pop_rank")
            en.physical["pop_band"] = (
                None if not rank else
                "1-3" if rank <= 3 else "4-6" if rank <= 6 else "7+")

        for band in ("1-3", "4-6", "7+"):
            members = [en for en in day_entries
                       if en.physical and en.physical["pop_band"] == band]
            for fld, key in (("jockey_idx", "joc_split"),
                             ("cyokyo_idx", "cyo_split")):
                have = sorted([en for en in members
                               if en.physical[fld] is not None],
                              key=lambda en: -en.physical[fld])
                cut = -(-len(have) // 2)  # ceil(n/2)
                for i, en in enumerate(have):
                    en.physical[key] = "high" if i < cut else "low"

        for en in day_entries:
            if not en.physical:
                continue
            js, cs = en.physical["joc_split"], en.physical["cyo_split"]
            band = en.physical["pop_band"]
            if not (js and cs and band):
                continue
            cell = f"{js}/{cs}"
            en.physical["v4_cell"] = cell
            en.physical["p_v4"] = cls.P_TABLE_V4[band][cell]

    def _load_results(self) -> None:
        """ZED(前走データ)全ファイルから馬ごとの着順履歴を集約する。

        異常走(中止・除外等)は系列に含めない。同一レースは重複排除。
        """
        if self._loaded_results:
            return
        self._loaded_results = True
        seen: set[tuple[str, str]] = set()
        for path in sorted(self.data_dir.glob("ZED[0-9]*.txt")):
            for row in parser.parse_records(path.read_bytes(), "ZED"):
                pid, ymd = row["pedigree_id"], row["ymd"]
                pos = parser.to_int(row["chakujun"])
                ijo = parser.to_int(row["ijo_kubun"]) or 0
                if not pid or not ymd or pos is None or pos < 1 or ijo != 0:
                    continue
                if (pid, ymd) in seen:
                    continue
                seen.add((pid, ymd))
                self._positions.setdefault(pid, []).append((ymd, pos))
        for pid in self._positions:
            self._positions[pid].sort(key=lambda t: t[0], reverse=True)  # 新しい順

    def get_recent_positions(self, horse_id: str) -> list[int] | None:
        self._load_results()
        hist = self._positions.get(horse_id)
        return [p for _, p in hist] if hist else None

    # ---------- DataProviderSet ----------
    def get_horse(self, horse_id: str) -> HorseDTO | None:
        self._load_masters()
        return self._horses.get(horse_id)

    def get_jockey(self, jockey_id: str) -> JockeyDTO | None:
        self._load_masters()
        return self._jockeys.get(jockey_id)

    def get_race(self, race_id: str) -> RaceDTO | None:
        # race_keyの年+data_dir走査では日付が引けないため、既ロード分から返す。
        # 未ロードの場合はdata_dir内の全BACを走査する
        if race_id in self._races:
            return self._races[race_id]
        for bac in sorted(self.data_dir.glob("BAC[0-9]*.txt")):
            ymd = bac.stem[3:]
            try:
                d = datetime.strptime(ymd, "%y%m%d").date()
            except ValueError:
                continue
            self._load_day(d)
            if race_id in self._races:
                return self._races[race_id]
        return None

    def list_races(self, race_date: date) -> list[RaceDTO]:
        self._load_day(race_date)
        return sorted((r for r in self._races.values() if r.race_date == race_date),
                      key=lambda r: (r.internal_id[:2], r.race_number))
