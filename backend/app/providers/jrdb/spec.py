"""JRDB固定長ファイルのレイアウト定義(データ)。

出典: JRDB公式仕様書(http://www.jrdb.com/program/data.html 配下、2026-07-16参照)
- BAC: bac_doc.txt   第4版d(レコード長184 ※改行CR/LF含む)
- KYI: kyi_doc.txt   第11版a(レコード長1024)
- UKC: ukc_doc.txt   第3版(レコード長292)
- KZA: Ks_doc1.txt   第1版b(レコード長272)
- OZ : Ozdata_doc.txt 第1版(レコード長957)

位置は仕様書どおり1始まりのバイト位置。文字コードはcp932(Shift-JIS)、
全角を含むためバイト単位でスライスする。占術知識は一切含まない(データ仕様のみ)。
必要な項目だけを定義する(全項目の網羅はしない)。
"""

# (start, length) 1始まりバイト位置
LAYOUTS: dict[str, dict] = {
    "BAC": {
        "record_len": 184,
        "fields": {
            "race_key":        (1, 8),    # 場2+年2+回1+日1(16進)+R2
            "yyyymmdd":        (9, 8),
            "start_hhmm":      (17, 4),
            "distance":        (21, 4),
            "track_code":      (25, 1),   # 1:芝, 2:ダート, 3:障害
            "kind_code":       (28, 2),   # 種別(コード表)
            "cond_code":       (30, 2),   # 条件
            "grade_code":      (36, 1),   # 0:非重賞 1:G1 2:G2 3:G3 4:重賞 5:特別L
            "race_name":       (37, 50),  # 全角25文字
            "head_count":      (95, 2),
            "race_name_short": (99, 8),
        },
    },
    "KYI": {
        "record_len": 1024,
        "fields": {
            "race_key":       (1, 8),
            "post_number":    (9, 2),     # 馬番
            "pedigree_id":    (11, 8),    # 血統登録番号(UKCとリンク)
            "horse_name":     (19, 36),
            "idm":            (55, 5),    # IDM(JRDB物理指数。ZZZ.Z)
            "jockey_idx":     (60, 5),    # 騎手指数
            "info_idx":       (65, 5),    # 情報指数
            "total_idx":      (85, 5),    # 総合指数
            "cyokyo_idx":     (145, 5),   # 調教指数(負値あり)
            "kyusha_idx":     (150, 5),   # 厩舎指数(負値あり)
            "base_win_odds":  (96, 5),    # 基準オッズ ZZ9.9(JRDB算出の想定オッズ)
            "base_win_rank":  (101, 2),   # 基準人気順位
            "base_place_odds": (103, 5),  # 基準複勝オッズ ZZ9.9
            "jockey_name":    (172, 12),
            "load_weight":    (184, 3),   # 0.1kg単位
            "jockey_code":    (336, 5),   # 騎手マスタ(KZA)とリンク
            "trainer_code":   (341, 5),
        },
    },
    "UKC": {
        "record_len": 292,
        "fields": {
            "pedigree_id":  (1, 8),
            "horse_name":   (9, 36),
            "sex_code":     (45, 1),      # 1:牡 2:牝 3:セン
            "sire_name":    (50, 36),
            "dam_name":     (86, 36),
            "birth_date":   (158, 8),     # YYYYMMDD
            "deleted_flag": (268, 1),     # 0:現役 1:抹消
        },
    },
    "KZA": {
        "record_len": 272,
        "fields": {
            "jockey_code":  (1, 5),
            "deleted_flag": (6, 1),
            "jockey_name":  (15, 12),
            "jockey_kana":  (27, 30),
            "birth_date":   (68, 8),      # YYYYMMDD
            "first_year":   (76, 4),
        },
    },
    # SED=成績データ(当日17時頃速報・木曜確定。検証=答え合わせ用)
    "SED": {
        "record_len": 376,
        "fields": {
            "race_key": (1, 8),
            "post_number": (9, 2),
            "pedigree_id": (11, 8),
            "ymd": (19, 8),
            "chakujun": (141, 2),
            "ijo_kubun": (143, 1),
            "ninki": (181, 2),
            "win_odds_final": (175, 6),  # 確定単勝オッズ
        },
    },
    # ZED=前走データ(過去5走分・成績データと同一フォーマット、レコード長376)
    "ZED": {
        "record_len": 376,
        "fields": {
            "pedigree_id": (11, 8),   # 血統登録番号
            "ymd": (19, 8),           # そのレースの年月日 YYYYMMDD
            "chakujun": (141, 2),     # 着順
            "ijo_kubun": (143, 1),    # 異常区分(0:正常)
            "ninki": (181, 2),        # 確定単勝人気順位(検証用に保持。スコア不使用)
        },
    },
    "OZ": {
        "record_len": 957,
        "fields": {
            "race_key":   (1, 8),
            "head_count": (9, 2),
            "win_odds":   (11, 90),   # 単勝オッズ ZZ9.9 × 18頭(馬番順)
            "place_odds": (101, 90),  # 複勝オッズ ZZ9.9 × 18頭
        },
        "odds_item_len": 5,
        "odds_count": 18,
    },
}

# JRA場コード(JRDBデータコード表準拠)
COURSE_CODES: dict[str, str] = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
}

SEX_CODES = {"1": "牡", "2": "牝", "3": "セン"}
TRACK_CODES = {"1": "turf", "2": "dirt", "3": "jump"}
GRADE_CODES = {"1": "G1", "2": "G2", "3": "G3", "4": "重賞", "5": "L", "6": "特別"}

# ファイル名: 種別 + yymmdd + .txt(配布時は .lzh / .zip 圧縮)
FILE_KINDS = ("BAC", "KYI", "UKC", "KZA", "OZ", "ZED", "SED")
