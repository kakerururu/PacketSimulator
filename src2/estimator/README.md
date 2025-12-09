# Estimator モジュール

## 概要

検出ログCSVから軌跡を推定するモジュール。

## アーキテクチャ

```
estimator/
├── domain/                      # ドメインモデル
│   ├── detection_record.py     # 検出レコード
│   ├── estimated_stay.py       # 推定された滞在
│   └── estimated_trajectory.py # 推定された軌跡
│
├── infrastructure/              # インフラ層
│   ├── csv_reader.py           # CSV読み込み
│   └── json_writer.py          # JSON出力
│
├── usecase/                     # ユースケース層
│   └── estimate_trajectories.py # 推定ロジック
│
└── main.py                      # エントリーポイント
```

## 推定処理フロー（予定）

### Phase 1: レコード収集と統合
1. **ログからハッシュ値ごとにレコードを収集**
   - CSVファイルから全検出レコードを読み込む
   - `hashed_id` ごとにレコードをグループ化
   - 時間順にソート

2. **類似ハッシュ値の統合**
   - 編集距離やその他の類似度指標を使用
   - 類似度が高いハッシュ値を同一の通行人と判定
   - 例: `C_01_base_hash` と `C_01_sub_hash` → `C_01_integrated`

   **元実装の例（src/evaluator）**:
   ```python
   # ハードコードされたペイロード統合ルール
   # 本来は編集距離による類似度が95%以上のものを統合すべき
   integrated_payload_mapping = {}
   for i in range(1, 11):
       base = f"C_{i:02d}_base_hash"
       sub = f"C_{i:02d}_sub_hash"
       integrated = f"C_{i:02d}_integrated"
       integrated_payload_mapping[base] = integrated
       integrated_payload_mapping[sub] = integrated
   ```

### Phase 2: クラスタリング
1. **ありえない移動の検出**
   - 時間的・空間的制約から物理的に不可能な移動を検出
   - 例: A地点 → B地点への移動が歩行速度では間に合わない

2. **クラスタの分割**
   - ありえない移動が検出された場合、別のクラスタ（別人）として分割
   - 各クラスタに `cluster_id` を割り当て

3. **経路推定**
   - 各クラスタの検出器訪問順序から経路文字列を生成
   - 例: A → B → C → D → "ABCD"

### Phase 3: 滞在時間推定
1. **滞在期間の推定**
   - 各検出器での最初/最後の検出時刻から滞在期間を推定
   - `estimated_arrival`, `estimated_departure` の計算

2. **EstimatedStay オブジェクトの生成**
   - 検出器ごとの滞在情報をオブジェクト化

3. **EstimatedTrajectory オブジェクトの生成**
   - クラスタごとに軌跡オブジェクトを生成

## データフロー

```
[CSV読み込み]
    ↓
[ハッシュ値ごとに収集]
    ↓
[類似ハッシュ統合] ← ここが重要！
    ↓
[クラスタリング]
    ↓
[経路推定]
    ↓
[滞在時間推定]
    ↓
[JSON出力]
```

## 現在の実装状況

### ✅ 完成
- Domain models (DetectionRecord, EstimatedStay, EstimatedTrajectory)
- CSV読み込み (csv_reader.py)
- JSON出力 (json_writer.py)
- エントリーポイント (main.py)

### ⏳ 未実装（スタブ）
- `estimate_trajectories.py` の実装
  - レコード収集ロジック
  - 類似ハッシュ統合ロジック
  - クラスタリングロジック
  - 経路推定ロジック
  - 滞在時間推定ロジック

## 元実装との対応

### src/evaluator との違い

| 項目 | src/evaluator | src2/estimator（予定） |
|------|--------------|---------------------|
| レコード収集 | `collect_and_sort_records` | 未実装 |
| 類似ハッシュ統合 | ハードコード（C_XX系のみ） | 汎用的な類似度計算 |
| クラスタリング | 3種類のロジック選択可能 | 再設計予定 |
| 出力形式 | dict | EstimatedTrajectory object |

### src/evaluator の classify_logic

元実装には3種類のクラスタリングロジックがありました:

1. **by_impossible_move.py**
   - ありえない移動のみで判定

2. **by_impossible_move_and_window.py**
   - ありえない移動 + 時間窓による判定

3. **window_max.py**
   - 時間窓の最大値による判定

これらのロジックは再設計時に参考にする予定です。

## 実装時の注意事項

### 類似ハッシュ統合の重要性

**なぜ必要か？**
- 同一デバイスでも状態によって異なるハッシュ値を送信する場合がある
- 例: `C_01_base_hash` (90%の確率) と `C_01_sub_hash` (10%の確率)
- これらを別人として扱うと人数が過大評価される

**統合方法の選択肢**:
1. ハードコード（モデル定義に基づく）
2. 編集距離による類似度計算（95%以上で統合）
3. シーケンス番号の連続性による判定
4. 時間・空間的な共起パターンによる判定

### クラスタリングの課題

**ありえない移動の判定基準**:
```python
# 疑似コード
min_travel_time = distance / walker_speed
actual_time_diff = record2.timestamp - record1.timestamp

if actual_time_diff < min_travel_time:
    # ありえない移動 → 別クラスタに分割
```

**エッジケース**:
- 検出の取りこぼし（一部の検出器で検出されない）
- 検出の重複（同一地点で複数回検出）
- タイムスタンプの精度

## 今後の実装計画

1. **Phase 1**: レコード収集と類似ハッシュ統合
2. **Phase 2**: 基本的なクラスタリング（ありえない移動検出）
3. **Phase 3**: 滞在時間推定
4. **Phase 4**: 複数のクラスタリングロジックの実装
5. **Phase 5**: 評価・改善

## 参考

- 元実装: `src/evaluator/`
- 設計書: `plan.md`
- Generator実装: `src2/generator/`
