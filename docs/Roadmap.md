# ロードマップ

## Phase 1: 動作する土台(完了 2026-07-12)

- [x] 正本v1.2の検証ローダー(SHA-256/サイズ/構文/キー/出典ID/語彙/day_theme鏡写し、degraded対応)
- [x] 共通DTO・DataProvider抽象・MockDataProvider・JRA-VANアダプター骨格
- [x] 占術エンジン(数秘/星座/数字×星座合成/年月日運。全て正本駆動)
- [x] 鑑定文生成+禁止語フィルタ(reject/redact)
- [x] REST API(/health, /v1/profile, /v1/day-fortune, /v1/readings/horse-triad)・OpenAPI 3.1
- [x] schema.sql適用(PostgreSQL/SQLite)・Docker Compose・pytest 9本

## Phase 2: 永続化と正本追随

- [x] 「今日のシンクロ度」v0の算出規則を定義(2026-07-16)。
      backend/app/knowledge/proposals/synchro_v0.json に規則を分離
      (構成要素と重み/10点正規化/5段階ラベル・色帯域/4象限パターン)。
      status=app_hypothesis・validation_required。**正本v1.3への収録提案が残タスク**
- [x] 集合意識係数の導入: 単勝オッズ=集合意識(市場の注目)の近似として
      対数尺度で10点化し、シンクロ度の一成分(重み0.25)とする。
      占術の流れ×集合意識の4象限(共鳴/隠れシンクロ/過熱/静観)を提示。
      ※現在はMockオッズ。実オッズはPhase 4のProvider経由
- [x] GET /v1/day-recommendations(今日のおすすめAPI): 対象日全出走の
      シンクロ度降順+最上位提示。タイブレークは物語性優先(hidden>resonance)。
      おすすめ=観戦の視点の提案であり、馬券購入の推奨・結果予測ではない
- [x] synchro_v0の正本v1.3収録**提案書**を作成(docs/proposals/KB_v1.3_synchro_v0_収録提案.md)。
      **正本側での収録・確定が残タスク** → 収録後、規則JSONを正本参照へ切替
- [x] readings永続化(2026-07-16): app_readingsテーブルへ鑑定履歴を保存
      (engine_ver=知識ベース版・rules_ver・score・応答全文JSON)。
      GET /v1/readings(一覧)・GET /v1/readings/{id}(詳細)を追加
- [x] Alembic導入(2026-07-16)。**方針**: Alembicはアプリ運用テーブル(app_*)のみを
      差分管理し、正本schema.sql由来の16テーブルには一切触れない(二正本の分離を維持)。
      正本テーブルは従来どおり起動時にDDL無変更適用。
      正本schema.sqlにreadings系の正式定義がある場合の統合は収録提案の確認事項に記載済み
- [x] フロントのAPI接続(2026-07-17): トップ「今日のおすすめ」とレース一覧が
      GET /v1/day-recommendations の実データを表示(API不達時はMockへフォールバック)。
      CORS許可・target_date省略時の直近開催日自動選択も実装。
      残: reading(4者分析)画面の実データ化(現状Mockレースのみ)
- [ ] triad統合スコアの正式定義を知識ベース側で確定 → エンジン反映(それまでvalidation_required)
- [ ] 知識ベースv1.3対応(ingress_eventsテーブル追加が正本側で確定した場合)

## Phase 3: エフェメリス(ephemeris_policy準拠)

- [ ] Skyfieldで太陽/月/木星/土星イングレス表を生成(成果物として版管理)
- [ ] astronomy_engineとの相互検算(5分以内)を品質ゲートに
- [ ] 境界日の厳密判定(boundary_flag解消)・レース日の月星座・木星土星年運のon_hold解除

## Phase 4: 実データとフロントエンド

- [x] **データ取得元の方針決定(2026-07-16)**: JV-LinkはWindows専用のため、
      Mac環境で完結する **JRDB(ベーシックコース)** を採用。
      HTTPダウンロード方式の正規データ提供サービス=horse_data_policy適合。
      **注意**: 個人利用契約のため、エンドユーザーへのデータ再配信には
      JRA商用契約(JRADB)が別途必要(サブスク公開前に照会必須)
- [x] JRDBアダプタ実装(2026-07-16): providers/jrdb/
      spec.py=公式仕様書由来のレイアウト定義(BAC/KYI/UKC/KZA/OZ)、
      parser.py=cp932固定長パーサ、adapter.py=共通DTO変換(name="jrdb")、
      fetch.py=会員認証ダウンロードワーカー骨格(zip/lzh展開)。
      合成フィクスチャで通しテスト済み(実データ不使用)
- [x] JRDB疎通完了(2026-07-17): 実データで36レース470頭のシンクロ度計算・
      禁止語ゼロ・履歴保存まで確認(2026-07-12開催分)。
      騎手マスタKZAはKs/配下。データ取得は backend/JRDB取得.command でも実行可
- [ ] パターン4象限の閾値調整: attention 5〜7の中間帯が「静観」に落ちるため、
      流れが強い馬が共鳴/隠れのどちらにも入らないケースがある。正本収録時に再設計
- [x] 戦績数秘・調律理論 choritsu/1.0(2026-07-17): 星読みターフ独自指標。
      着順の並びを質変換し、位相/律/弾性/基調の4信号で「並びが整いつつあるか」を
      0-10点化。ZED(前走データ)から実着順を取得(異常走除外)。
      オッズ・人気は不使用(市場から独立・検証の循環回避)。
      解析器レジストリ方式で検証後のv2/学習版に差替可能。app_hypothesis。
      検証計画: app_readings蓄積→調律スコア×次走の質の順位相関(人気統制付き)
- [ ] オッズの位置づけ改善: 現在の「基準オッズ」はJRDB算出の想定オッズ
      (=専門家の集合意識の近似)。発走直前の実売オッズ(=大衆の集合意識)は
      TYB(直前データ)対応で実現する
- [x] 定時取得のスケジューラ化(2026-07-17): launchdで木・金・土21:00に
      当日+翌日分を自動取得(scripts/jrdb_auto_fetch.py+plist)。
      セットアップは backend/自動取得を設定.command のダブルクリック
- [ ] Windows取得ワーカー(JV-Link)は将来のオプションに格下げ(JRDBで代替)
- [ ] Next.js(TypeScript/PWA)フロントエンド
- [x] GitHub Actions CI(pytest+lint)

## Phase 5: AI補助・検証・サブスクリプション

- [ ] AI文章補助の接続(文章化のみ。禁止語フィルタ通過必須・計算の主体にしない)
- [ ] verification_planに基づく統計検証(出生月統制等の交絡制御を必須記載)
- [ ] 検証結果の知識ベースへの反映提案(hypothesis→validated/not_supported)
- [ ] サブスクリプション開始(認証・決済・鑑定履歴)。方針はMONETIZATION.md。
      前提: 実データ+実オッズ(Phase 4)により集合意識係数が本物になること

## 原則(全Phase共通)

知識ベース(Google Drive正本)とコード(GitHub正本)の分離を維持。
未確定の重みを確定しない・仮説を事実として扱わない・秘密情報をコミットしない。
