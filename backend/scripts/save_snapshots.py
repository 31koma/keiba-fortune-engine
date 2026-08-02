"""レース前スナップショットの自動保存(launchdから金・土の夜と土・日の朝に実行)。

- 今日と明日のうち、レースがある日の day_recommendation(客観・oshi_v0)を
  計算して app_readings に保存する(「過去レースを見る」の事前評価になる)
- 同一条件の保存が既にあれば何もしない(アプリを開いた時と同じ重複回避)
- その日の最初のレースが発走した後は保存しない(発走後の保存は
  過去レース画面の誠実ゲートで事前評価と認められないため、無駄な保存をしない)
- ログは logs/snapshot.log(Git管理外)
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db import repository  # noqa: E402
from app.db.migrate import upgrade_app_schema  # noqa: E402
from app.domain.engine.numerology import Numerology  # noqa: E402
from app.domain.engine.oshi import OshiEngine  # noqa: E402
from app.domain.engine.synchro import SynchroEngine  # noqa: E402
from app.domain.engine.wordfilter import ForbiddenFilter  # noqa: E402
from app.knowledge.loader import load_knowledge  # noqa: E402
from app.providers import base as providers_base  # noqa: E402
from app.providers import jrdb  # noqa: F401,E402 (プロバイダ登録のため)
from app.providers import mock  # noqa: F401,E402
from app.services.recommend import RecommendService  # noqa: E402


def first_start(races) -> str | None:
    times = [r.start_time for r in races if r.start_time]
    return min(times) if times else None


def main() -> None:
    now = datetime.now()  # Macのローカル時刻=JST
    today = date.today()
    print(f"=== スナップショット自動保存 {now:%Y-%m-%d %H:%M} 実行 ===")

    kb = load_knowledge(settings.kb_dir, settings.manifest_md)
    if kb.report.status != "ok":
        print(f"中止: 知識ベースが検証不一致です: {kb.report.problems}")
        return
    try:
        upgrade_app_schema()
    except Exception as e:  # noqa: BLE001 スキーマ適用失敗は保存時に顕在化する
        print(f"注意: スキーマ適用に失敗({type(e).__name__}: {e})")

    num = Numerology(kb, keep_masters_in_cycles=settings.keep_masters_in_cycles)
    ff = ForbiddenFilter(kb, mode=settings.forbidden_filter_mode)
    provider = providers_base.create_provider(settings.data_provider)
    from app.domain.engine.zodiac import Zodiac
    rec = RecommendService(SynchroEngine(kb, num, Zodiac(kb)), ff, provider,
                           OshiEngine())
    credit = {
        "data_provider_name": settings.data_provider_name,
        "data_provider_credit": settings.data_provider_credit,
        "data_provider_license_status": settings.data_provider_license_status,
    }

    for t in (today, today + timedelta(days=1)):
        label = t.isoformat()
        races = provider.list_races(t)
        if not races:
            print(f"--- {label}: レースデータなし(スキップ)")
            continue
        existing = repository.find_reading_id(
            "day_recommendation", kb.report.version, "oshi_v0", t, None)
        if existing is not None:
            print(f"--- {label}: 保存済み(reading_id={existing}、スキップ)")
            continue
        start = first_start(races)
        if t == today and start and now.strftime("%H:%M") >= start:
            print(f"--- {label}: 最初の発走({start})を過ぎているため保存しない"
                  "(発走後の保存は事前評価になりません)")
            continue
        try:
            result = rec.day_recommendations(t, None, credit)
        except Exception as e:  # noqa: BLE001 1日分の失敗で他を止めない
            print(f"--- {label}: 計算エラー {type(e).__name__}: {e}")
            continue
        if not result.get("items"):
            print(f"--- {label}: 0頭のため保存しない(出走馬マスタ等の"
                  "データ不足。次回実行時に再試行します)")
            continue
        top = result.get("recommendation") or {}
        rid = repository.save_reading(
            "day_recommendation", kb.report.version, result,
            target_date=t, user_birth_date=None,
            race_id=top.get("race_id"), horse_id=top.get("horse_id"),
            jockey_id=top.get("jockey_id"), rules_ver="oshi_v0",
            score=(top.get("oshi") or {}).get("score"))
        if rid is None:
            print(f"--- {label}: 保存に失敗しました(DBを確認してください)")
        else:
            print(f"--- {label}: 保存しました(reading_id={rid}、"
                  f"{len(result['items'])}頭、発走前チェックOK)")


if __name__ == "__main__":
    main()
