# 競走馬占術エンジン (keiba-fortune-engine)

**数秘術・西洋占星術で「競走馬・騎手・レース日・利用者」4者の関係性を読み、競馬をより深く楽しむためのエンターテインメントを提供するプロジェクト。**

> 本鑑定はエンターテインメントであり、レース結果を予測・保証するものではありません。

このREADMEは単なる説明書ではなく、初めて参加するAI・開発者・将来の自分が最初に読む**このプロジェクトの入口**です。3〜5分で全体を把握できます。

---

## 目次

1. [まず最初に読むドキュメント](#まず最初に読むドキュメント)
2. [プロジェクト概要](#プロジェクト概要)
3. [システム全体像](#システム全体像)
4. [リポジトリ構成](#リポジトリ構成)
5. [現在の完成状況](#現在の完成状況)
6. [起動方法](#起動方法)
7. [開発フロー](#開発フロー)
8. [開発ルール(5つの掟)](#開発ルール5つの掟)
9. [ロードマップ](#ロードマップ)
10. [このプロジェクトを一文で](#このプロジェクトを一文で)

---

## まず最初に読むドキュメント

参加者(AI・開発者)は、作業前に必ずこの順で読んでください。

| 順 | ドキュメント | 役割(一行) |
|---|---|---|
| 1 | [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) | 何を目指し、何を絶対に守るかを定めた**プロジェクト憲法**(最上位・全判断の基準) |
| 2 | [PRODUCT_EXPERIENCE.md](PRODUCT_EXPERIENCE.md) | 利用者にどんな**体験**(感情の流れ・答えの出し方)を提供するかの定義書 |
| 3 | [AI_STYLE_GUIDE.md](AI_STYLE_GUIDE.md) | 利用者と対話するAIの**人格・話し方・回答品質**の定義書 |
| 4 | [BRAND_GUIDELINES.md](BRAND_GUIDELINES.md) | 世界観・色・言葉——**ブランド**としての一貫性を定めた指針 |

技術詳細は [docs/Architecture.md](docs/Architecture.md)(層構成)・[docs/KnowledgeBase.md](docs/KnowledgeBase.md)(知識ベース13ファイル)・[docs/Roadmap.md](docs/Roadmap.md)(フェーズ計画)へ。

## プロジェクト概要

- **目的**: 競馬予想を"当てる"ことではない。**競走馬・騎手・レース日・利用者**の4者の占術的な関係性を分析し、競馬をより深く楽しむエンターテインメントを提供する
- **理念**: 主役は利用者。占術は体験を支えるエンジン。仮説を事実として扱わず、未来を保証する表現を使わない
- **特徴**:
  - 占術計算は知識ベース+決定的プログラム(AIは文章化・説明・比較・対話のみ)
  - 知識(意味・ルール・テンプレート・禁止語)をコードに書かない**データ駆動設計**
  - データ取得元(JRA-VAN等)に固定依存しない**DataProvider交換式**
  - 利用者ごとに変わる「自分だけの鑑定」と、必ず提示される「今回の結論」

## システム全体像

```
┌─────────────────────────────┐
│   Google Drive = 知識の唯一の正本            │
│   (占術知識ベース vX.Y / JSON12本+schema.sql) │
└──────────────┬──────────────┘
               ↓  起動時にサイズ+SHA-256検証(不一致はdegraded)
┌──────────────┴──────────────┐
│ Knowledge Engine(knowledge/)               │ 検証ロード・整合チェック
└──────────────┬──────────────┘
               ↓
┌──────────────┴──────────────┐
│ Fortune Engine(domain/engine/)             │ 数秘・星座・合成・年月日運の決定的計算
│  + 鑑定文生成 + 禁止語フィルタ                │
└──────────────┬──────────────┘
               ↓
┌──────────────┴──────────────┐
│ AI(ai/gateway ※未接続)                     │ 文章化・説明・比較・対話のみ
└──────────────┬──────────────┘
               ↓
┌──────────────┴──────────────┐
│ REST API(FastAPI / OpenAPI 3.1)            │ /health /v1/profile /v1/day-fortune /v1/readings/*
└──────────────┬──────────────┘
               ↓
┌──────────────┴──────────────┐
│ Webアプリ(将来: Next.js/PWA)                │ 4者分析の体験を届ける画面
└─────────────────────────────┘

  馬・レース データ提供元(JRA-VAN/NAR/CSV…) ⇒ DataProvider変換層 ⇒ 共通DTO ⇒ 上記エンジンへ
```

**二正本の思想**: **Google Drive=知識の唯一の正本 / GitHub=コードの唯一の正本**。
知識ベースを差し替えてもコードを書き換えない。コードを読んでも占術の中身は分からない(意味はすべて正本にある)。この分離が本プロジェクトの背骨です。

## リポジトリ構成

```
競馬アプリ/
├ README.md                  # 本書(入口)
├ PROJECT_PRINCIPLES.md      # 開発憲章(最上位)
├ PRODUCT_EXPERIENCE.md      # 体験定義書
├ AI_STYLE_GUIDE.md          # AI人格定義書
├ BRAND_GUIDELINES.md        # ブランドガイドライン
├ 正本参照.md                 # 知識ベース正本のハッシュ表(起動時検証の基準)
├ docker-compose.yml         # PostgreSQL + API(開発用)
├ .env.example               # 設定例(秘密情報はコミット禁止)
├ docs/                      # Architecture / KnowledgeBase / Roadmap
└ backend/
  ├ app/
  │ ├ main.py                # FastAPI エントリポイント(OpenAPI 3.1)
  │ ├ core/                  # 設定・共通例外(知識は持たない)
  │ ├ knowledge/             # 正本の検証ローダー(Knowledge Engine)
  │ ├ domain/
  │ │ ├ dto.py               # 共通DTO(Horse/Jockey/Race)
  │ │ └ engine/              # 占術エンジン(Fortune Engine)+文章生成+禁止語
  │ ├ providers/             # DataProvider抽象+mock+jravan骨格
  │ ├ services/              # ユースケース(profile/day-fortune/triad)
  │ ├ db/                    # SQLAlchemy2・schema.sql適用
  │ └ ai/                    # AI連携口(未接続スタブ)
  └ tests/                   # pytest(起動検証・改ざん検知・計算・API通し)
```

※ 知識ベース本体はリポジトリに**含めません**(二正本の分離)。

## 現在の完成状況

| 領域 | 状態 | 備考 |
|---|---|---|
| 知識ベース(JSON12本+schema.sql) | ✅ 完成 | 正本v1.2(2026-07-12凍結)・全整合検査パス |
| 知識検証ローダー(SHA-256/degraded) | ✅ 完成 | 改ざん検知テスト済み |
| 占術エンジン(数秘・星座・合成・日運) | ✅ 完成 | 全て正本駆動・決定的計算 |
| 鑑定文生成+禁止語フィルタ | ✅ 完成 | 生成文の禁止語ゼロ実測済み |
| REST API基盤(4エンドポイント) | ✅ 完成 | OpenAPI 3.1・pytest 9本パス |
| DB(schema.sql適用) | ✅ 完成 | PostgreSQL/SQLite・16テーブル |
| Docker Compose | ✅ 完成 | db+api |
| GitHub管理 | ✅ 完成 | main・Private |
| 思想ドキュメント4部 | ✅ 完成 | 憲章・体験・AI人格・ブランド |
| DataProvider(実データ) | 🚧 未着手 | 現在はMock。Windows取得ワーカーは別プロジェクト予定 |
| triad統合スコア | 🚧 保留 | 正本側で定義確定待ち(validation_required) |
| エフェメリス(イングレス表) | 🚧 未着手 | ephemeris_policy準拠でPhase 3 |
| Frontend(Next.js/PWA) | 🚧 未着手 | Phase 4 |
| AI API接続 | 🚧 未着手 | Phase 5(文章補助のみ) |
| readings永続化/Alembic/CI | 🚧 未着手 | Phase 2 |

## 起動方法

```bash
# 前提: 知識ベースフォルダと正本参照.mdの場所を設定(.env.example参照)

# Docker(PostgreSQL)
docker compose up --build

# ローカル(SQLiteフォールバック)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000/docs

# テスト
pytest tests/
```

起動後 `GET /health` で知識ベースの検証結果(版・ロード数・問題)を確認できます。

## 開発フロー

新しい機能を追加するときの基本の流れ:

```
思想(憲章・体験定義に適合するか確認)
  ↓
知識ベース(必要な知識・ルールは正本側へ追加提案 → 版更新 → 正本参照.md更新)
  ↓
実装(コードはロジックのみ。知識をハードコードしない)
  ↓
テスト(決定的計算・改ざん検知・禁止語ゼロ・API通し)
  ↓
GitHub(feature/* → Pull Request → main)
  ↓
リリース(SemVer・engine_verに知識ベース版を記録)
```

## 開発ルール(5つの掟)

1. **知識はGoogle Drive** — 占術の意味・ルール・テンプレートの正本はDrive。アプリは検証して読むだけ
2. **コードはGitHub** — 実装・テスト・文書の正本はこのリポジトリ。mainは常にリリース可能に
3. **知識をハードコードしない** — 不足があれば補完せず、正本への追加を提案する
4. **AIは勝手に占術を追加しない** — 計算は知識ベースが決定。AIは語り部に徹する
5. **品質優先** — 完成より継続、速度より品質。迷ったら「5年後も保守できる実装」を選ぶ

詳細は [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) 参照。

## ロードマップ

| 段階 | 内容 |
|---|---|
| **現在(完了)** | 知識ベースv1.2凍結・検証ローダー・占術エンジン・REST API・Mock Provider・Docker・思想ドキュメント4部 |
| **次** | readings永続化・Alembic・CI(GitHub Actions)・triad統合スコアの正本側確定→実装・エフェメリス(イングレス表生成と境界日厳密判定) |
| **将来** | 実データProvider(Windows取得ワーカー連携)・Next.jsフロントエンド(PWA)・AI文章補助の接続・利用者を加えた4者分析の完成・検証設計に基づく統計検証 |

詳細は [docs/Roadmap.md](docs/Roadmap.md) 参照。

---

## このプロジェクトを一文で

> **「当てる」を約束しない誠実さと、「面白い」を約束する設計で、星と数字がいつものレースを自分だけの物語に変える。**

ようこそ。まずは [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) から読み始めてください。
