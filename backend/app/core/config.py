"""アプリ設定。占術の知識・意味・ルールは一切保持しない(正本=知識ベースdb/)。"""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT = Path(__file__).resolve().parents[2]  # backend/
PROJECT_ROOT = APP_ROOT.parent                   # 競馬アプリ/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KEIBA_", env_file=".env", extra="ignore")

    # --- 知識ベース(唯一の正本) ---
    kb_dir: Path = PROJECT_ROOT.parent / "KomaVault" / "05_Knowledge" / "占術知識ベース_v1.3"
    # 2026-08-02: v1.3へ版上げ(13→17ファイル。oshi_v0/sizhu_day_pillar/wuxing_correspondences/
    # racecourse_geography を収録)。v1.2は凍結。
    # 2026-08-02: 正本をKomaVaultへ移設(Googleドライブ撤退に伴う憲章第2条改訂)。
    # 旧: PROJECT_ROOT.parent / "黄道十二宮、西洋占星術、数秘術" / "db"(凍結・参照しない)
    manifest_md: Path = PROJECT_ROOT / "正本参照.md"  # MANIFEST_正本v1.3の写し(ハッシュ表)
    strict_startup: bool = False  # True: 検証不一致で起動失敗 / False: degraded状態で起動

    # --- DB ---
    database_url: str = "sqlite:///./data/app.db"  # 本番はdocker-composeでPostgreSQLを注入
    apply_schema_on_startup: bool = True

    # --- DataProvider ---
    data_provider: str = "mock"
    data_provider_name: str = "Mock Data Provider"
    data_provider_credit: str = "データ提供: モック(開発用固定データ)"
    data_provider_license_status: str = "development_only"

    # --- JRDB(実データ。個人利用契約・再配信にはJRA商用契約が別途必要) ---
    jrdb_data_dir: Path = APP_ROOT / "data" / "jrdb"  # 展開済み.txtの置き場
    jrdb_base_url: str = "http://www.jrdb.com/member/data"  # 会員登録後に実パス確認
    jrdb_user: str = ""       # .envで設定(コミット禁止)
    jrdb_password: str = ""   # .envで設定(コミット禁止)

    # --- ログイン認証(単一ユーザー。外部公開時の入口の鍵) ---
    # 平文パスワードはここにも.envにも置かない。ハッシュだけを置く
    # (生成は「パスワード設定.command」。詳細は app/core/auth.py)
    auth_required: bool = True          # False にすると認証なしで開く(ローカル専用時のみ)
    auth_email: str = ""                # ログインに使うメールアドレス
    auth_password_hash: str = ""        # pbkdf2_sha256$回数$salt$hash
    auth_secret: str = ""               # セッション署名鍵。変更すると全セッションが失効する
    auth_session_days: int = 30         # ログインの保持日数(スマホで毎回入力しなくて済む長さ)

    # --- 禁止語フィルタ(語彙は正本から。ここはモードのみ) ---
    forbidden_filter_mode: Literal["reject", "redact", "regenerate"] = "reject"

    # --- 流派オプション(正本でstatus=school_specificの項目のみ切替可) ---
    master_33_enabled: bool = True          # 正本注記「33を認めない流派あり。設定でOFF可」
    keep_masters_in_cycles: bool = True     # 正本既定「保持(Decoz準拠)。設定で1桁還元に切替可」

    # --- AI補助(実接続はまだ行わない) ---
    ai_enabled: bool = False


settings = Settings()
