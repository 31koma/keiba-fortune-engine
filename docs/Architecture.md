# アーキテクチャ

## 方針

モジュラーモノリス。DataProvider層を独立モジュールとして分離し、将来必要な場合のみ
マイクロサービス化できる構成。Windows依存処理(JV-Link)は別ワーカーへ切り離す前提で、
Webアプリ本体はLinux/Dockerで完結する。

## データフロー(厳守)

```
データ提供元(JRA-VAN/CSV/REST/SFTP…)
  ↓ DataProvider変換層(providers/)      … 取得元を交換可能に抽象化
共通DTO(domain/dto.py)・共通DB形式(schema.sql)
  ↓ 占術エンジン(domain/engine/)         … 知識ベース駆動の決定的計算
鑑定文生成(textgen)→禁止語フィルタ(wordfilter) … 生成後フィルタ必須
  ↓ AI文章補助(ai/gateway)               … 現在未接続。文章化のみに限定
REST API(main.py, OpenAPI 3.1)
  ↓
Webアプリ(将来: Next.js/PWA)
```

## レイヤー責務

| レイヤー | 場所 | 責務 | 禁止事項 |
|---|---|---|---|
| knowledge | app/knowledge/ | 正本13ファイルの検証ロード(サイズ/SHA-256/構文/必須キー/出典ID/語彙/day_theme鏡写し)、degraded管理 | フォールバック補完 |
| providers | app/providers/ | 取得元→共通DTO変換。mock / jravan骨格 | 占術知識への依存 |
| domain/engine | app/domain/engine/ | 数秘・星座・数字×星座合成(step0〜5)・年月日運の層規則。全パラメータは正本から | 知識・重みのハードコード |
| services | app/services/ | ユースケース組み立て(profile/day-fortune/triad)、免責・クレジット注入 | 未確定重みの確定 |
| api | app/main.py | REST/OpenAPI、503(degraded)/422(knowledge_gap)/500(禁止語) | 取得方式への直接依存 |
| db | app/db/ | SQLAlchemy2接続、正本schema.sql適用(SQLite時のみ機械的方言変換) | 正本DDLの意味変更 |
| ai | app/ai/ | 文章補助の連携口(未接続スタブ) | 占術計算の主体化 |

## エラー設計

- 正本不一致: strict=起動失敗 / 非strict=degraded(/healthで詳細、鑑定系APIは503)
- 知識不足: 422 `knowledge_gap` を返し、正本側への追加提案を促す(補完しない)
- 禁止語検出: mode=reject(500で拒否) / redact(伏字) / regenerate(AI接続後)

## OS・インフラ分離

- Windows側(将来別プロジェクト): JV-Link取得ワーカー → 共通DTO変換 → Web側DB/キュー送信
- Web側(本リポジトリ): Linux/Docker/PostgreSQL/REST/エンジン/UI。Windows依存コードゼロ
