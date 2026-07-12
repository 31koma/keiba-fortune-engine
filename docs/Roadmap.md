# ロードマップ

## Phase 1: 動作する土台(完了 2026-07-12)

- [x] 正本v1.2の検証ローダー(SHA-256/サイズ/構文/キー/出典ID/語彙/day_theme鏡写し、degraded対応)
- [x] 共通DTO・DataProvider抽象・MockDataProvider・JRA-VANアダプター骨格
- [x] 占術エンジン(数秘/星座/数字×星座合成/年月日運。全て正本駆動)
- [x] 鑑定文生成+禁止語フィルタ(reject/redact)
- [x] REST API(/health, /v1/profile, /v1/day-fortune, /v1/readings/horse-triad)・OpenAPI 3.1
- [x] schema.sql適用(PostgreSQL/SQLite)・Docker Compose・pytest 9本

## Phase 2: 永続化と正本追随

- [ ] triad統合スコアの正式定義を知識ベース側で確定 → エンジン反映(それまでvalidation_required)
- [ ] readings/entities等へのDB永続化(engine_ver=正本版を記録)
- [ ] Alembic導入(schema.sql正本を基準とした差分管理)
- [ ] 知識ベースv1.3対応(ingress_eventsテーブル追加が正本側で確定した場合)

## Phase 3: エフェメリス(ephemeris_policy準拠)

- [ ] Skyfieldで太陽/月/木星/土星イングレス表を生成(成果物として版管理)
- [ ] astronomy_engineとの相互検算(5分以内)を品質ゲートに
- [ ] 境界日の厳密判定(boundary_flag解消)・レース日の月星座・木星土星年運のon_hold解除

## Phase 4: 実データとフロントエンド

- [ ] Windows取得ワーカー(JV-Link→共通DTO→DB/キュー)を別プロジェクトで構築
- [ ] 実Provider実装(法務チェックリスト=horse_data_policy準拠。スクレイピング禁止)
- [ ] Next.js(TypeScript/PWA)フロントエンド
- [ ] GitHub Actions CI(pytest+lint)

## Phase 5: AI補助と検証

- [ ] AI文章補助の接続(文章化のみ。禁止語フィルタ通過必須・計算の主体にしない)
- [ ] verification_planに基づく統計検証(出生月統制等の交絡制御を必須記載)
- [ ] 検証結果の知識ベースへの反映提案(hypothesis→validated/not_supported)

## 原則(全Phase共通)

知識ベース(Google Drive正本)とコード(GitHub正本)の分離を維持。
未確定の重みを確定しない・仮説を事実として扱わない・秘密情報をコミットしない。
