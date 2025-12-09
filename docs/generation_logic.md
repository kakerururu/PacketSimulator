# Generator 生成ロジック詳細解説

## 全体フロー

```
1. 設定読み込み
   ├─ detectors.jsonc → 検出器の位置情報
   ├─ payloads.jsonc → モデルとペイロードの確率分布
   └─ simulation_settings.jsonc → シミュレーションパラメータ

2. 通行人生成 (generate_walkers)
   ├─ N人の通行人を生成
   └─ 各通行人に対して:
       ├─ ランダムなルート生成 (例: "ACBD")
       ├─ モデルを確率的に選択 (例: Model_C_08)
       └─ ペイロード割り当て:
           ├─ dynamic_unique_payload=true → 固定ID生成
           └─ dynamic_unique_payload=false → None (後で確率分布から選択)

3. シミュレーション実行
   └─ 各通行人に対して:
       ├─ 滞在タイムライン生成 (generate_stay_timeline)
       │   └─ ルート上の各検出器で:
       │       ├─ 到着時刻 = 現在時刻
       │       ├─ 滞在時間 = random(180-420秒)
       │       ├─ 出発時刻 = 到着時刻 + 滞在時間
       │       └─ 次の検出器へ移動:
       │           ├─ 移動時間 = 距離 / 速度 ± ばらつき
       │           └─ 現在時刻 = 出発時刻 + 移動時間
       │
       ├─ 軌跡オブジェクト生成 (Trajectory)
       │   └─ Ground Truth として保存
       │
       └─ 検出レコード生成 (generate_detection_records)
           └─ 各滞在期間中に:
               ├─ 連続ペイロード生成:
               │   ├─ 開始オフセット = random(0, 滞在時間-3ms)
               │   └─ 3つの連続レコード (シーケンス番号が連続)
               │       └─ タイムスタンプ間隔: 1ms
               │
               └─ ランダムペイロード生成:
                   ├─ 残り27個のレコード
                   ├─ 各レコード:
                   │   ├─ タイムスタンプ = random(滞在期間内)
                   │   ├─ ペイロード = 確率分布から選択
                   │   └─ シーケンス番号 = random(0-4095)
                   └─ 全レコードをタイムスタンプでソート

4. 出力
   ├─ Ground Truth JSON:
   │   └─ 軌跡情報 (到着・出発時刻、滞在時間)
   └─ 検出ログ CSV:
       └─ 検出器ごとにグループ化された検出レコード
```

## 詳細ステップ

### Step 1: 通行人生成

```python
# 例: 2人の通行人を生成
Walker_1:
  - model: "Model_C_08"
  - route: "ACBD"
  - assigned_hash_ID: None (確率分布型)

Walker_2:
  - model: "Model_Group_A_DynamicUnique"
  - route: "BDCA"
  - assigned_hash_ID: "unique_and_hashed_payload_Walker_2" (固定)
```

### Step 2: 滞在タイムライン生成

```python
# Walker_1 の例 (ルート: "ACBD")
シミュレーション開始: 2024-01-14 11:00:00

A検出器:
  - 到着: 11:00:00
  - 滞在時間: 314.5秒 (random 180-420)
  - 出発: 11:05:14.5

移動 A→C:
  - 距離: 141.4m (ユークリッド距離)
  - 移動時間: 101.0秒 (141.4/1.4 ± 10%)
  - 次の到着: 11:06:55.5

C検出器:
  - 到着: 11:06:55.5
  - 滞在時間: 267.3秒
  - 出発: 11:11:22.8

... (以下同様に B, D と続く)
```

### Step 3: 検出レコード生成

```python
# A検出器での滞在中 (11:00:00 ~ 11:05:14.5)
# 合計30個のレコードを生成

連続ペイロード (3個):
  - 開始オフセット: 45.2秒 (random)
  - Record 1: 11:00:45.200, seq=1234, payload=C_08_base_payload
  - Record 2: 11:00:45.201, seq=1235, payload=C_08_base_payload
  - Record 3: 11:00:45.202, seq=1236, payload=C_08_base_payload

ランダムペイロード (27個):
  - Record 4: 11:00:12.5, seq=789, payload=C_08_base_payload
  - Record 5: 11:01:23.8, seq=2341, payload=C_08_sub_payload
  - Record 6: 11:02:45.1, seq=156, payload=C_08_base_payload
  ... (27個続く、各レコードは確率分布に基づいてペイロード選択)

最終出力: タイムスタンプでソートされた30レコード
```

### Step 4: ペイロード選択ロジック

```python
# Model_C_08 の場合
payload_distribution = {
    "C_08_base_payload": 0.9,  # 90%の確率
    "C_08_sub_payload": 0.1    # 10%の確率
}

各レコード生成時:
  random_choice([
      "C_08_base_payload",
      "C_08_sub_payload"
  ], weights=[0.9, 0.1])

→ 統計的に 30レコード中 約27個が base、約3個が sub
```

## 時間計算の詳細

### 移動時間計算

```python
# A(0,0) から C(100,100) への移動
distance = sqrt((100-0)^2 + (100-0)^2) = 141.4m
base_time = 141.4 / 1.4 = 101.0秒
variation = 101.0 * 0.1 * random(-1, 1) = ±10.1秒
actual_time = 101.0 + variation  # 例: 95.3秒 or 107.8秒
```

### レコード配置

```
滞在期間: [到着時刻 ━━━━━━━━━━━━━━━━━━ 出発時刻]
          0秒                           314.5秒

連続レコード配置:
          [━━━━━━━━━●●●━━━━━━━━━━━━━━━━]
                    45.2秒位置に3つ (1ms間隔)

ランダムレコード配置:
          [━●━━●━━━━●●●━●━━●━━━●━●━━━━●━]
           ランダムに27個が散らばる
```

## 出力フォーマット

### Ground Truth JSON
```json
{
  "metadata": {
    "generation_timestamp": "2025-12-08 11:00:00.000",
    "num_walkers": 2,
    "num_detectors": 4,
    "num_trajectories": 2
  },
  "trajectories": [
    {
      "trajectory_id": "gt_traj_1",
      "walker_id": "Walker_1",
      "route": "ACBD",
      "timeline": [
        {
          "detector_id": "A",
          "arrival_time": "2024-01-14 11:00:00.000",
          "departure_time": "2024-01-14 11:05:14.500",
          "duration_seconds": 314.5
        },
        // ... C, B, D
      ]
    }
  ]
}
```

### 検出ログ CSV (A_log.csv)
```csv
Timestamp,Walker_ID,Hashed_Payload,Detector_ID,Sequence_Number
2024-01-14 11:00:12.500,Walker_1,C_08_base_payload,A,789
2024-01-14 11:00:45.200,Walker_1,C_08_base_payload,A,1234
2024-01-14 11:00:45.201,Walker_1,C_08_base_payload,A,1235
2024-01-14 11:00:45.202,Walker_1,C_08_base_payload,A,1236
...
```

## キーポイント

1. **確率的要素**:
   - ルート順序: ランダムシャッフル
   - モデル選択: 確率分布
   - 滞在時間: 一様分布 (180-420秒)
   - 移動時間: ±10%のばらつき
   - ペイロード選択: モデルごとの確率分布

2. **時系列の一貫性**:
   - 各検出器での到着時刻は前の出発時刻+移動時間
   - レコードのタイムスタンプは必ず滞在期間内
   - 検出器間の移動時間は物理的距離に基づく

3. **現実的なシミュレーション**:
   - 連続ペイロード: 実際の端末が短時間に複数パケット送信
   - ランダムペイロード: 散発的な通信パターン
   - シーケンス番号: 連続型とランダム型の混在
