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
| 5 | [MONETIZATION.md](MONETIZATION.md) | サブスクリプション設計——何を売り、何を売らないかの**収益方針** |

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
├ MONETIZATION.md            # サブスクリプション設計(何を売り、何を売らないか)
├ 星読みターフを起動.command   # ワンクリック起動(停止/取得/自動設定も同様)
├ docs/                      # Architecture / KnowledgeBase / Roadmap / proposals(正本収録提案)
├ frontend/                  # Next.js 14(実データ稼働)
│ ├ app/                     # 画面(トップ/races/reading/you/compat/plans)+components
│ └ lib/                     # api(APIクライアント)/synchro・synchroModes(規則の鏡写し)
└ backend/
  ├ app/
  │ ├ main.py                # FastAPI エントリポイント(OpenAPI 3.1)
  │ ├ core/                  # 設定・共通例外(知識は持たない)
  │ ├ knowledge/             # 正本の検証ローダー(Knowledge Engine)
  │ │ └ proposals/           # 正本収録候補の規則(synchro_v0.json=app_hypothesis)
  │ ├ domain/
  │ │ ├ dto.py               # 共通DTO(Horse/Jockey/Race)
  │ │ └ engine/              # 占術エンジン+synchro(シンクロ度)+pattern_numerology(調律)
  │ ├ providers/             # DataProvider抽象+mock+jrdb(実データ)+jravan骨格
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
| 鑑定文生成+禁止語フィルタ | ✅ 完成 | 生成文の禁止語ゼロ実測済み(実データ470頭でも確認) |
| REST API基盤(7エンドポイント) | ✅ 完成 | OpenAPI 3.1・pytest 16本パス。CORS・開催日自動探索対応 |
| シンクロ度v0+今日のおすすめ | ✅ 実データ稼働 | synchro_v0規則(app_hypothesis)。集合意識=オッズ係数化。正本v1.3収録提案書作成済(docs/proposals/) |
| 調律スコア(戦績数秘・独自指標) | ✅ 実データ稼働 | choritsu/1.0。着順の並び→位相/律/弾性/基調の4信号。ZED実戦績駆動・オッズ不使用。検証前仮説 |
| DataProvider(実データ) | ✅ 稼働中 | JRDB(ベーシック)接続済。BAC/KYI/UKC/KZA/OZ/ZED/SED取得。木金土日21時自動取得(launchd)。個人利用契約=再配信にはJRA商用契約要 |
| Frontend(Next.js) | ✅ 実データ稼働 | IPAT式ドリルダウン(場→レース→馬)・4指標ストリップ(総/客/本/数)・詳細シート4タブ・ディープリンク。API不達時はMockフォールバック |
| 鑑定履歴(app_readings) | ✅ 完成 | engine_ver記録・重複保存防止・起動時ハウスキーピング。Alembicはapp_*専用 |
| DB(schema.sql適用) | ✅ 完成 | PostgreSQL/SQLite・16テーブル |
| Docker Compose / CI | ✅ 完成 | db+api / push・PRで整合・pytest・禁止語・OpenAPI自動検査 |
| 思想ドキュメント | ✅ 完成 | 憲章・体験・AI人格・ブランド+MONETIZATION(サブスク方針) |
| triad統合スコア | 🚧 保留 | 正本側で定義確定待ち(validation_required) |
| 統計検証(答え合わせ) | 🚧 蓄積中 | SED(結果)を毎週自動取得。数開催週たまり次第バックテスト |
| エフェメリス(イングレス表) | 🚧 未着手 | ephemeris_policy準拠でPhase 3 |
| サブスクリプション | 🚧 構想 | /plansプレビュー公開済。決済・認証はPhase 5 |
| AI API接続 | 🚧 未着手 | Phase 5(文章補助のみ) |
| reading(4者分析)画面の実データ化 | 🚧 未着手 | 現状Mockレースのみ。次の候補タスク |

## 起動方法(日常運用)

Finderでのダブルクリックだけで動きます:

| ファイル | 役割 |
|---|---|
| **星読みターフを起動.command** | バックエンド+フロントエンドを起動しブラウザを開く(コード更新時は自動再ビルド) |
| **星読みターフを停止.command** | 全部止める |
| **backend/JRDB取得.command** | データを手動取得(今日+明日+直近週末) |
| **backend/自動取得を設定.command** | 木・金・土・日 21:00の自動取得をMacに登録 |

開発者向け(ターミナル):

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt lhafile
.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app  # API
.venv/bin/python -m pytest tests/                                   # テスト
cd ../frontend && npm run build && npm run start                    # 画面
```

起動後 `GET /health` で知識ベースの検証結果・プロバイダ状態を確認できます。

## データの置き場所と容量

すべて `backend/data/` 配下(Git管理外)に貯まります。

| 場所 | 中身 | 増え方の目安 |
|---|---|---|
| `data/jrdb/*.txt` | JRDB生データ(出走表・オッズ・戦績・結果) | 約2MB/開催日 → **年間約0.2GB** |
| `data/app.db` | 鑑定履歴(検証用)・SQLite | 重複保存防止+起動時自動掃除で **数十MB規模** |

年間合計でも0.5GB未満の想定で、Macが重くなる心配はありません。
生データを消してもアプリは動きます(戦績・結果の履歴だけ失われる)。

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
| **現在(完了)** | 知識ベースv1.2・占術エンジン・JRDB実データ接続(自動取得)・シンクロ度v0・調律スコア(独自指標)・4指標UI・鑑定履歴・サブスク方針 |
| **次** | 結果データ蓄積→統計検証(調律スコア・シンクロ度の答え合わせ)・synchro_v0とtriadの正本側確定・reading画面の実データ化・直前オッズ(TYB) |
| **将来** | PWA化・AI文章補助の接続・サブスク開始(要JRA商用契約照会)・エフェメリス(Phase 3) |

詳細は [docs/Roadmap.md](docs/Roadmap.md) 参照。

---

## このプロジェクトを一文で

> **「当てる」を約束しない誠実さと、「面白い」を約束する設計で、星と数字がいつものレースを自分だけの物語に変える。**

ようこそ。まずは [PROJECT_PRINCIPLES.md](PROJECT_PRINCIPLES.md) から読み始めてください。
