# 知識ベース(唯一の正本)

## 正本の場所と版

- **正本**: `KomaVault/05_Knowledge/占術知識ベース_v1.3`(現行版・2026-08-02発行)
  - v1.2は同フォルダ階層に凍結(2026-08-02にGoogle Driveから移設したもの)。旧: 黄道十二宮、西洋占星術、数秘術/db も凍結
- 基準: `正本参照.md`(MANIFEST_正本v1.3の写し。17ファイルのサイズ+SHA-256先頭16桁)
- 旧版(v1.1、01〜08フォルダ内のスナップショット)は参照禁止
- 版更新手順: KomaVault/05_Knowledge/ に `占術知識ベース_vX.Y` を新設→MANIFEST後継発行→
  `正本参照.md` のハッシュ表を更新(コード変更不要で切替できる設計を維持)

## 17ファイルの役割(v1.3)

| ファイル | 内容 |
|---|---|
| numerology_core.json | 数秘の体系(ピタゴラス式letter_values)・還元法(Decoz)・計算式・意味・グループ相性 |
| zodiac_core.json | 12星座(トロピカル・サンサイン)・元素/活動宮・distance法/element法相性・時期運 |
| interpretation_templates.json | 数字13種+星座12種×13部品(essence/strengths/4軸レベル等) |
| number_zodiac_combinations.json | 数字×星座の合成規則step0〜5(部品選択/4軸平均/シナジー行列/ギャップ/マスター/重複統合) |
| horse_expression_templates.json | 馬向け語り口テンプレート・プレースホルダ定義・禁止語・免責文 |
| human_expression_templates.json | 人向け語り口テンプレート |
| temporal_cycles.json | 年運/月運/日運テーマ・層規則(前景=日/中景=月/背景=年)・適用可否行列 |
| sources_master.json | 出典の唯一の正(全ファイルはsource_idsで参照) |
| status_vocab.json | ステータス語彙4族(解釈/採否/検証/事実)+注記規則 |
| ephemeris_policy.json | 天体計算ポリシー(イングレス表方式・正午法・tzdb・Skyfield採用) |
| horse_data_policy.json | 馬名正規化(公式英字優先)・入力最小要件・法務チェックリスト |
| verification_plan.json | 事前登録の検証仮説・交絡統制(出生月統制等) |
| schema.sql | DBスキーマ(PostgreSQL想定・16テーブル) |
| oshi_v0.json | おすすめ(推し度)v0。収束(本質×調律)を核とする最終評価の算出規則+adjustersレジストリ【v1.3収録】 |
| sizhu_day_pillar.json | 四柱推命の日柱(十干十支・十干類象・五行・干合支合)【v1.3収録】 |
| wuxing_correspondences.json | 五行の方位・色・季節・時刻・味の配当+職業傾向【v1.3収録】 |
| racecourse_geography.json | JRA10場の座標・回り方向・方位角算出規則・方位→五行(地運)【v1.3収録】 |

## アプリ側の遵守事項

1. 起動時に13ファイルを検証(存在/サイズ/SHA-256/JSON構文/必須キー/出典ID/語彙/day_theme鏡写し)
2. 不一致は起動失敗またはdegraded。黙って継続しない
3. 知識・意味・ルール・テンプレート・禁止語・重み・仮説ステータスをコードへハードコードしない
4. 不足・矛盾はknowledge_gapとして明示し、正本側への追加提案として報告する
5. day_themeの正はnumerology_core.meanings(temporal_cyclesはミラー、ロード時一致検査)

## 既知の未確定事項(正本側で確定待ち)

- triad(馬×騎手×レース日)の統合スコア・最終重み → API は unweighted raw features +
  validation_required を返す(暫定バンドはzodiac.combined_score使用と明示)
- ingress_events テーブルのschema.sql追加(ephemeris_policy.storage_note、v1.3候補)
- エフェメリス導入までjupiter_saturn_year / moon_day は on_hold

> **v1.3注記(2026-08-02)**: `synchro_v0.json` は収録見送り。重み「あなた×馬0.20」が同日の決定「共鳴は材料に降格」と矛盾するため、重みを見直すかoshiへ一本化するまで `backend/app/knowledge/proposals/` に留置する。
