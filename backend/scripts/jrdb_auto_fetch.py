"""JRDB定期取得(launchdから木・金・土の夜に実行される)。

- 今日と明日の2日分を取得する(前日19時配布=金曜夜に土曜分、土曜夜に日曜分)
- 木曜は騎手マスタKZA等の週次更新を拾う
- 未配布(404)はスキップされるだけなので、多めに叩いても害はない
- ログは logs/jrdb_fetch.log(Git管理外)
"""
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.jrdb.fetch import fetch_day  # noqa: E402

RETRIES = 3          # 一時的なDNS/ネット断に備えた再試行回数
RETRY_WAIT_SEC = 30


def main() -> None:
    today = date.today()
    targets = [today, today + timedelta(days=1)]
    print(f"=== JRDB自動取得 {today.isoformat()} 実行 ===")
    for t in targets:
        print(f"--- {t.isoformat()} ---")
        for attempt in range(1, RETRIES + 1):
            try:
                for p in fetch_day(t):
                    print(f"  {p}")
                break
            except Exception as e:  # noqa: BLE001 1日分の失敗で他を止めない
                print(f"  エラー(試行{attempt}/{RETRIES}): {type(e).__name__}: {e}")
                if attempt < RETRIES:
                    time.sleep(RETRY_WAIT_SEC)


if __name__ == "__main__":
    main()
