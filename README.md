# 競走馬占術エンジン Webアプリ (keiba-fortune-engine)

数秘術・西洋占星術の知識ベースに基づき、競走馬・騎手・レース日を分析する
エンターテインメントWebアプリ。**本鑑定はレース結果を予測・保証するものではありません。**

## プロジェクト概要

- 競走馬・騎手・レース日のデータを、数秘術と西洋占星術の知識ベースで決定的に分析し、
  競馬予想の補助となるエンターテインメントコンテンツ(プロフィール鑑定・日運・三者鑑定)をREST APIで提供する
- データ取得元(JRA-VAN等)に依存しない疎結合設計(DataProvider層で交換可能)
- AIは占術計算の主体にしない(将来、文章補助のみに限定して接続)

## 役割分担(固定方針)

| 正本 | 場所 | 内容 |
|---|---|---|
| **占術知識ベースの正本** | Google Drive「占術アプリ知識ベース/00_正本_知識ベース_v1.2_20260712」(ローカル作業正本=「黄道十二宮、西洋占星術、数秘術/db」) | JSON 12本+schema.sql。数字・星座の意味、相性ルール、年月日運、鑑定文テンプレート、禁止語、出典、仮説ステータス |
| **ソースコードの正本** | GitHub(本リポジトリ) | アプリ実装・テスト・ドキュメント |

- 知識ベースはリポジトリに**含めない**。起動時に外部フォルダから検証ロードする
- 基準ハッシュは `正本参照.md`(MANIFEST_正本v1.2の写し)。サイズ+SHA-256不一致は
  strict=起動失敗 / 非strict=degraded(鑑定系API 503)。黙ってフォールバックしない
- 知識・意味・ルール・テンプレート・禁止語・重みのハードコード禁止。
  不足・矛盾はアプリ側で補完せず、知識ベースへの追加提案として報告する

## 開発環境

- Python 3.12 / FastAPI / Pydantic v2 / SQLAlchemy 2 / PostgreSQL 16(開発時SQLiteフォールバック可)
- Docker Compose(Linux)。Webアプリ本体にWindows依存コードなし
  (JRA-VAN/JV-Link連携は将来、別プロジェクトのWindowsワーカーが担当)
- テスト: pytest

## 起動方法

```bash
# 1) 知識ベースフォルダと正本参照.mdの場所を設定(.env.example参照)
# 2) Docker(PostgreSQL)
docker compose up --build
# または ローカル(SQLite)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000/docs
# テスト
pytest tests/
```

主要API: `GET /health` / `GET /v1/profile` / `GET /v1/day-fortune` / `POST /v1/readings/horse-triad`
(詳細は docs/Architecture.md と OpenAPI /docs)

## 今後のロードマップ

docs/Roadmap.md 参照。概要:

1. **Phase 1(完了)**: 正本検証ローダー・占術エンジン・Mock Provider・REST API・テスト
2. **Phase 2**: triad統合スコアの正式定義(知識ベース側で確定→実装)、readingsのDB永続化、Alembic導入
3. **Phase 3**: エフェメリス(イングレス表生成=Skyfield、境界日厳密判定・月星座)
4. **Phase 4**: 実データProvider(Windows取得ワーカー+キュー/DB連携)、Next.jsフロントエンド(PWA)
5. **Phase 5**: AI文章補助の接続(禁止語フィルタ通過必須)、検証設計(verification_plan)に基づく統計検証

## リポジトリ構成

```
├ 正本参照.md            # 正本v1.2ハッシュ表(起動時検証の基準)
├ docker-compose.yml
├ .env.example           # 秘密情報はコミット禁止(.gitignoreで.envを除外)
├ docs/                  # Architecture / KnowledgeBase / Roadmap
└ backend/
  ├ app/                 # main(API) / core / knowledge / domain / providers / services / db / ai
  └ tests/
```
