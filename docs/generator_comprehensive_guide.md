# Generator モジュール 包括的ガイド

## 目次

1. [概要](#概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [ディレクトリ構造](#ディレクトリ構造)
4. [ドメインモデル](#ドメインモデル)
5. [インフラストラクチャ層](#インフラストラクチャ層)
6. [ユースケース層](#ユースケース層)
7. [設定ファイル](#設定ファイル)
8. [データフロー](#データフロー)
9. [実行方法](#実行方法)
10. [設計の意図](#設計の意図)

---

## 概要

Generator モジュールは、スマートフォン検出による人流追跡シミュレーターのデータ生成を担当します。

### 主な機能

1. **通行人の生成**: スマートフォンモデルとルートを持つ通行人を生成
2. **滞在リスト生成**: 各検出器での滞在情報（到着・出発時刻）を生成
3. **検出レコード生成**: 滞在期間中の検出レコード（ペイロード）を生成
4. **Ground Truth 出力**: 完全な軌跡情報をJSONで出力
5. **検出ログ出力**: 検出器ごとのログをCSVで出力

### 出力データ

- **Ground Truth JSON**: `src2_result/ground_truth/trajectories.json`
  - 各通行人の完全な軌跡情報
  - 到着・出発時刻、滞在時間を含む

- **検出ログ CSV**: `src2_result/detector_logs/{A,B,C,D}_log.csv`
  - 検出器ごとの検出レコード
  - タイムスタンプ、Walker ID、ペイロード、シーケンス番号

---

## アーキテクチャ

### レイヤードアーキテクチャ

```
┌─────────────────────────────────────┐
│         main.py (Entry Point)       │
│  設定読み込み + シミュレーション実行  │
└────────────┬────────────────────────┘
             │
             ↓
┌────────────────────────────────────┐
│       Usecase Layer (Business)      │
│  - walker_generation.py            │
│  - stay_generation.py              │
│  - record_generation.py            │
│  - simulation.py                   │
└────────────┬───────────────────────┘
             │
             ↓
┌────────────────────────────────────┐
│     Infrastructure Layer (I/O)      │
│  - config_loader.py                │
│  - csv_writer.py                   │
│  - json_writer.py                  │
│  - utils.py (utilities)            │
└────────────┬───────────────────────┘
             │
             ↓
┌────────────────────────────────────┐
│       Domain Layer (Models)         │
│  - Walker                          │
│  - Trajectory                      │
│  - Stay                            │
│  - DetectionRecord                 │
│  - PayloadModel (型定義)           │
└────────────────────────────────────┘
```

### 責務の分離

- **Domain**: ビジネスの概念（通行人、軌跡、滞在など）
- **Usecase**: ビジネスロジック（生成アルゴリズム）
- **Infrastructure**: 外部システムとのやり取り（ファイルI/O）
- **Main**: エントリーポイント（全体の調整）

---

## ディレクトリ構造

```
src2/generator/
├── domain/                      # ドメインモデル
│   ├── __init__.py
│   ├── walker.py               # 通行人
│   ├── trajectory.py           # 軌跡（Ground Truth）
│   ├── stay.py                 # 滞在情報
│   ├── detection_record.py     # 検出レコード
│   └── payload_config.py       # ペイロード設定の型定義
│
├── infrastructure/              # インフラストラクチャ層
│   ├── __init__.py
│   ├── config_loader.py        # 設定ファイル読み込み
│   ├── csv_writer.py           # CSV出力
│   ├── json_writer.py          # JSON出力
│   └── utils.py                # 共通ユーティリティ
│
├── usecase/                     # ユースケース層
│   ├── __init__.py
│   ├── walker_generation.py    # 通行人生成
│   ├── stay_generation.py      # 滞在リスト生成
│   ├── record_generation.py    # レコード生成
│   └── simulation.py           # シミュレーション実行
│
└── main.py                      # エントリーポイント
```

---

## ドメインモデル

### Walker (通行人)

**ファイル**: `domain/walker.py`

```python
@dataclass
class Walker:
    id: str          # 通行人ID（例: "Walker_1"）
    model: str       # スマートフォンモデル（例: "Model_C_08"）
    route: str       # 移動ルート（例: "ABCD"）
```

**説明**:
- シミュレーション上の歩行者を表現
- 各通行人はスマートフォンを持ち、特定のルートを移動
- ペイロードの決定はレコード生成時に行われる

**設計の意図**:
- シンプルな構造（ペイロード情報を含まない）
- ペイロードロジックはユースケース層に委譲

### Stay (滞在)

**ファイル**: `domain/stay.py`

```python
@dataclass
class Stay:
    detector_id: str           # 検出器ID（例: "A"）
    arrival_time: datetime     # 到着時刻
    departure_time: datetime   # 出発時刻
    duration_seconds: float    # 滞在時間（秒）
```

**説明**:
- 1つの検出器での滞在情報
- Ground Truth の基本単位

### Trajectory (軌跡)

**ファイル**: `domain/trajectory.py`

```python
@dataclass
class Trajectory:
    trajectory_id: str      # 軌跡ID（例: "gt_traj_1"）
    walker_id: str          # 通行人ID（例: "Walker_1"）
    route: str              # ルート（例: "ABCD"）
    stays: List[Stay]       # 滞在情報のリスト（時系列順）
```

**説明**:
- 通行人が複数の検出器を訪問した経路の実際の記録
- シミュレーションで生成される Ground Truth データ
- `stays`フィールドには時系列順に並んだ滞在情報が格納される

### DetectionRecord (検出レコード)

**ファイル**: `domain/detection_record.py`

```python
@dataclass
class DetectionRecord:
    timestamp: datetime        # 検出時刻
    walker_id: str            # 通行人ID（Ground Truth用）
    hashed_id: str            # ハッシュ化されたペイロード
    detector_id: str          # 検出器ID
    sequence_number: int      # シーケンス番号（0-4095）
```

**説明**:
- 検出ログに記録される1行のデータ
- CSV出力の1レコードに対応

### PayloadModel (ペイロード設定の型定義)

**ファイル**: `domain/payload_config.py`

```python
class PayloadModel(TypedDict):
    overall_probability: float         # モデルの選択確率
    is_unique: bool                    # ユニークペイロードか
    payload_distribution: Dict[str, float]  # ペイロード確率分布
```

**説明**:
- `config/payloads.jsonc` の型定義
- ユニーク型: `is_unique=True`, `payload_distribution={}`
- その他: `is_unique=False`, `payload_distribution={...}`

---

## インフラストラクチャ層

### config_loader.py

**責務**: 設定ファイルの読み込み

#### 主要関数

##### `load_jsonc(file_path: str) -> Dict[str, Any]`
- JSONCファイル（コメント付きJSON）を読み込む
- 行コメント `//` とブロックコメント `/* */` を除去

##### `load_detectors() -> List[Detector]`
- `config/detectors.jsonc` から検出器設定を読み込む
- 返り値: `List[Detector]`

##### `load_payloads() -> Tuple[PayloadDefinitionsDict, List[str], List[float]]`
- `config/payloads.jsonc` からペイロード設定を読み込む
- 返り値:
  - `PayloadDefinitionsDict`: モデルごとのペイロード定義
  - `List[str]`: モデル名のリスト
  - `List[float]`: モデルの選択確率のリスト

##### `load_simulation_settings(config_dir: str) -> Dict[str, Any]`
- `config/simulation_settings.jsonc` からシミュレーション設定を読み込む
- デフォルト値を設定:
  - `stay_duration_min_seconds`: 180
  - `stay_duration_max_seconds`: 420

### csv_writer.py

**責務**: 検出ログのCSV出力

#### 主要関数

##### `write_detector_logs(records: List[DetectionRecord], output_dir_path: str)`
- 検出レコードを検出器ごとのCSVファイルに書き込む
- ファイル名: `{detector_id}_log.csv`
- タイムスタンプでソートして出力
- デフォルト出力先: `src2_result/detector_logs/`

**CSV フォーマット**:
```csv
Timestamp,Walker_ID,Hashed_Payload,Detector_ID,Sequence_Number
2024-01-14 11:00:05.123,Walker_1,C_01_base_payload,A,100
```

### json_writer.py

**責務**: Ground Truth のJSON出力

#### 主要関数

##### `write_ground_truth(trajectories: List[Trajectory])`
- Ground Truth JSONを書き込む
- 設定ファイルから `num_walkers` と `num_detectors` を自動取得
- デフォルト出力先: `src2_result/ground_truth/trajectories.json`

**JSON フォーマット**:
```json
{
  "metadata": {
    "generation_timestamp": "2025-12-08 11:00:00.000",
    "num_walkers": 10,
    "num_detectors": 4,
    "num_trajectories": 10
  },
  "trajectories": [
    {
      "trajectory_id": "gt_traj_1",
      "walker_id": "Walker_1",
      "route": "ABCD",
      "stays": [
        {
          "detector_id": "A",
          "arrival_time": "2024-01-14 11:00:00.000",
          "departure_time": "2024-01-14 11:05:00.000",
          "duration_seconds": 300.0
        }
      ]
    }
  ]
}
```

### utils.py

**責務**: 共通ユーティリティ関数

#### 主要関数

##### `format_timestamp(dt: datetime) -> str`
- datetime オブジェクトをミリ秒まで含む文字列に変換
- フォーマット: `YYYY-MM-DD HH:MM:SS.mmm`
- 例: `"2024-01-14 11:00:05.123"`

---

## ユースケース層

### walker_generation.py

**責務**: 通行人の生成とルート割り当て

#### 主要関数

##### `generate_random_route(detectors: List[Detector]) -> str`
- ランダムなルート文字列を生成
- アルゴリズム: 検出器IDをシャッフルして連結
- 例: `["A", "B", "C", "D"]` → `"DBCA"`

##### `generate_walkers(...) -> List[Walker]`
- 指定された数の通行人を生成
- 各通行人に:
  1. モデルを確率的に割り当て
  2. ランダムなルートを生成
  3. Walker オブジェクトを作成

**パラメータ**:
- `num_walkers`: 生成する通行人の数
- `detectors`: 検出器のリスト
- `payload_definitions`: ペイロード定義
- `model_names`: モデル名のリスト
- `model_probabilities`: モデルの選択確率

**処理フロー**:
```
1. for i in range(num_walkers):
2.   walker_id = f"Walker_{i + 1}"
3.   assigned_model = random.choices(model_names, weights=model_probabilities)[0]
4.   route = generate_random_route(detectors)
5.   walkers.append(Walker(id, model, route))
6. return walkers
```

### stay_generation.py

**責務**: 滞在リストの生成と移動時間計算

#### 主要関数

##### `calculate_moving_time_from_detector_to_detector(...) -> float`
- 2つの検出器間の移動時間を計算
- アルゴリズム:
  1. ユークリッド距離を計算
  2. 基本移動時間 = 距離 / 速度
  3. ランダムなばらつきを追加（±variation_factor）

**パラメータ**:
- `from_detector`: 出発検出器
- `to_detector`: 到着検出器
- `walker_speed`: 通行人の移動速度 (m/s)
- `variation_factor`: 速度のばらつき係数

**計算式**:
```python
distance = sqrt((x2-x1)^2 + (y2-y1)^2)
base_time = distance / speed
variation = base_time * variation_factor * random(-1, 1)
travel_time = max(0, base_time + variation)
```

##### `generate_stays(route, detectors, start_time) -> List[Stay]`
- ルートに基づいて滞在リストを生成
- **設定ファイルから数値パラメータを自動読み込み**

**パラメータ**:
- `route`: ルート文字列（例: "ABCD"）
- `detectors`: 検出器の辞書 `{id: Detector}`
- `start_time`: シミュレーション開始時刻

**設定ファイルから読み込む値**:
- `stay_duration_min_seconds`: 最小滞在時間（秒）
- `stay_duration_max_seconds`: 最大滞在時間（秒）
- `walker_speed`: 通行人の移動速度 (m/s)
- `variation_factor`: 速度のばらつき係数

**処理フロー**:
```
1. settings = load_simulation_settings()  # 設定読み込み
2. stay_duration_min = settings["stay_duration_min_seconds"]
3. stay_duration_max = settings["stay_duration_max_seconds"]
4. walker_speed = settings["walker_speed"]
5. variation_factor = settings["variation_factor"]

6. current_time = start_time

7. for each detector in route:
     a. arrival_time = current_time
     b. stay_duration = random.uniform(min, max)  # 180-420秒
     c. departure_time = arrival_time + stay_duration
     d. stays.append(Stay(...))

     e. if not last detector:
          travel_time = calculate_moving_time_from_detector_to_detector(
              current, next, walker_speed, variation_factor
          )
          current_time = departure_time + travel_time

8. return stays
```

**設計の意図**:
- 呼び出し側がパラメータを知る必要がない
- 設定ファイルが唯一の真実の情報源（Single Source of Truth）
- 関数シグネチャがシンプル

### record_generation.py

**責務**: 検出レコードの生成とペイロード選択

#### 主要関数

##### `choose_payload(walker_id: str, model_name: str, ...) -> str`
- レコード生成時にペイロードを選択
- **ユニーク型モデル** (`is_unique=True`):
  - `walker_id` に基づいて固定ペイロードを生成
  - 例: `"unique_and_hashed_payload_Walker_1"`
  - 全レコードで同じペイロードを使用
- **その他のモデル** (`is_unique=False`):
  - 確率分布に基づいて毎回選択
  - 例: `"C_08_base_payload"` (90%) or `"C_08_sub_payload"` (10%)

**処理フロー**:
```python
if payload_definitions[model_name]["is_unique"]:
    # ユニーク型: 固定ペイロード
    return f"unique_and_hashed_payload_{walker_id}"
else:
    # 確率分布型: 毎回選択
    distribution = payload_definitions[model_name]["payload_distribution"]
    return random.choices(payload_types, weights=probabilities)[0]
```

##### `generate_detection_records(walker, stays, ...) -> List[DetectionRecord]`
- 滞在リストから検出レコードを生成

**パラメータ**:
- `walker`: 通行人オブジェクト
- `stays`: 滞在リスト（`List[Stay]`）
- `payload_definitions`: ペイロード定義
- `payloads_per_detector`: 各検出器での検出数
- `num_consecutive_payloads`: 連続ペイロード数

**処理フロー**:
```
for each stay in stays:
  records = []

  # 1. 連続ペイロードの生成（シーケンス番号が連続）
  if num_consecutive_payloads > 0:
    start_offset = random(0, stay_duration - 3ms)
    seq = random(0, 4095)
    for k in range(num_consecutive_payloads):
      time = arrival + start_offset + k*1ms
      payload = choose_payload(walker_id, model)
      records.append(DetectionRecord(time, walker_id, payload, detector, seq))
      seq = (seq + 1) % 4096

  # 2. ランダムペイロードの生成
  for _ in range(num_random_payloads):
    offset = random(0, stay_duration)
    time = arrival + offset
    payload = choose_payload(walker_id, model)
    seq = random(0, 4095)
    records.append(DetectionRecord(time, walker_id, payload, detector, seq))

  # 3. タイムスタンプでソート
  records.sort(by timestamp)

return all_records
```

### simulation.py

**責務**: 各ユースケースを組み合わせてシミュレーション全体を実行

#### 主要関数

##### `run_simulation(...) -> Tuple[List[Trajectory], List[DetectionRecord]]`
- シミュレーション全体のオーケストレーション

**パラメータ**:
- `detectors`: 検出器のリスト
- `payload_definitions`: ペイロード定義
- `model_names`: モデル名のリスト
- `model_probabilities`: モデルの選択確率
- `num_walkers`: 生成する通行人の数
- `start_time`: シミュレーション開始時刻
- `payloads_per_detector`: 各検出器での検出数
- `num_consecutive_payloads`: 連続ペイロード数

**処理フロー**:
```
1. detector_dict = {d.id: d for d in detectors}  # 辞書に変換

2. walkers = walker_generation.generate_walkers(...)

3. for each walker:
     # 滞在リスト生成（設定ファイルから自動読み込み）
     stays = stay_generation.generate_stays(
         walker.route, detector_dict, start_time
     )

     # 軌跡作成
     trajectory = Trajectory(
         trajectory_id=f"gt_traj_{i+1}",
         walker_id=walker.id,
         route=walker.route,
         stays=stays
     )

     # レコード生成
     records = record_generation.generate_detection_records(
         walker, stays, payload_definitions,
         payloads_per_detector, num_consecutive_payloads
     )

     trajectories.append(trajectory)
     all_records.extend(records)

4. return trajectories, all_records
```

**設計の意図**:
- 各ユースケースの結果を組み合わせる役割に専念
- 設定値は各ユースケースで読み込む（疎結合）

---

## 設定ファイル

### detectors.jsonc

**場所**: `config/detectors.jsonc`

**内容**:
```jsonc
{
  "detectors": [
    {"id": "A", "x": 0.0, "y": 0.0},
    {"id": "B", "x": 100.0, "y": 0.0},
    {"id": "C", "x": 100.0, "y": 100.0},
    {"id": "D", "x": 0.0, "y": 100.0}
  ]
}
```

**説明**: 検出器の位置情報を定義

### payloads.jsonc

**場所**: `config/payloads.jsonc`

**構造**:
```jsonc
{
  "models": {
    "Model_Group_A_DynamicUnique": {
      "overall_probability": 0.20,
      "is_unique": true,
      "payload_distribution": {}
    },
    "Model_C_08": {
      "overall_probability": 0.035,
      "is_unique": false,
      "payload_distribution": {
        "C_08_base_payload": 0.9,
        "C_08_sub_payload": 0.1
      }
    }
  }
}
```

**フィールド説明**:
- `overall_probability`: このモデルが選ばれる確率
- `is_unique`: ユニークペイロードを持つか
- `payload_distribution`: ペイロードの確率分布
  - ユニーク型: 空の辞書 `{}`
  - その他: ペイロード名と確率のマッピング

**モデルタイプ**:

1. **ユニーク型** (Model A)
   - `is_unique: true`
   - 常に1種類のペイロードのみ
   - 他のどのモデルとも衝突しない

2. **一般型** (Model B)
   - `is_unique: false`
   - 1種類のペイロードのみ（確率1.0）
   - 他モデルと衝突する可能性あり

3. **限定変動型** (Model C)
   - `is_unique: false`
   - 複数のペイロード（類似している）
   - 例: 90% base, 10% sub

4. **変動型** (Model D)
   - `is_unique: false`
   - 複数のペイロード（類似していない）
   - 例: 30% state1, 30% state2, 40% state3

### simulation_settings.jsonc

**場所**: `config/simulation_settings.jsonc`

**内容**:
```jsonc
{
  "simulation_settings": {
    "num_walkers_to_simulate": 10,
    "payloads_per_detector_per_walker": 30,
    "num_consecutive_payloads": 3,
    "walker_speed": 1.4,
    "variation_factor": 0.1,
    "stay_duration_min_seconds": 180,
    "stay_duration_max_seconds": 420
  }
}
```

**フィールド説明**:
- `num_walkers_to_simulate`: シミュレートする通行人数
- `payloads_per_detector_per_walker`: 各検出器での検出数
- `num_consecutive_payloads`: 連続ペイロード数（シーケンス番号連続）
- `walker_speed`: 通行人の移動速度 (m/s)
- `variation_factor`: 移動速度のばらつき係数
- `stay_duration_min_seconds`: 最小滞在時間（秒）
- `stay_duration_max_seconds`: 最大滞在時間（秒）

---

## データフロー

### 全体フロー

```
┌─────────────────────────────────────────────┐
│ 1. 設定ファイル読み込み                      │
│    - detectors.jsonc                        │
│    - payloads.jsonc                         │
│    - simulation_settings.jsonc              │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 2. 通行人生成 (walker_generation)           │
│    - N人の通行人を生成                       │
│    - 各通行人にモデルとルートを割り当て       │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 3. 各通行人に対して:                        │
│    ┌─────────────────────────────────────┐ │
│    │ 3.1 滞在リスト生成                   │ │
│    │     (stay_generation)               │ │
│    │     - 設定ファイルから数値読み込み    │ │
│    │     - ルート上の各検出器での滞在情報  │ │
│    │     - 到着・出発時刻を計算           │ │
│    └─────────────┬───────────────────────┘ │
│                  ↓                          │
│    ┌─────────────────────────────────────┐ │
│    │ 3.2 軌跡オブジェクト作成             │ │
│    │     (Trajectory)                    │ │
│    │     - stays フィールドに格納         │ │
│    │     - Ground Truth として保存       │ │
│    └─────────────┬───────────────────────┘ │
│                  ↓                          │
│    ┌─────────────────────────────────────┐ │
│    │ 3.3 検出レコード生成                │ │
│    │     (record_generation)             │ │
│    │     - 連続ペイロード (3個)          │ │
│    │     - ランダムペイロード (27個)      │ │
│    └─────────────────────────────────────┘ │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ 4. 出力                                     │
│    ┌─────────────────────────────────────┐ │
│    │ Ground Truth JSON                   │ │
│    │ (json_writer)                       │ │
│    │ → src2_result/ground_truth/         │ │
│    └─────────────────────────────────────┘ │
│    ┌─────────────────────────────────────┐ │
│    │ 検出ログ CSV                        │ │
│    │ (csv_writer)                        │ │
│    │ → src2_result/detector_logs/        │ │
│    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### タイムライン生成の詳細

```
Walker_1 (ルート: "ACBD")
シミュレーション開始: 2024-01-14 11:00:00

┌─────────────────────────────────────────┐
│ A検出器                                  │
│ 到着: 11:00:00                          │
│ 滞在: 314.5秒 (random 180-420)          │
│ 出発: 11:05:14.5                        │
└─────────────────────────────────────────┘
         ↓ 移動 (101.0秒)
┌─────────────────────────────────────────┐
│ C検出器                                  │
│ 到着: 11:06:55.5                        │
│ 滞在: 267.3秒                           │
│ 出発: 11:11:22.8                        │
└─────────────────────────────────────────┘
         ↓ 移動
┌─────────────────────────────────────────┐
│ B検出器                                  │
│ ...                                     │
└─────────────────────────────────────────┘
         ↓ 移動
┌─────────────────────────────────────────┐
│ D検出器                                  │
│ ...                                     │
└─────────────────────────────────────────┘
```

### レコード生成の詳細

```
A検出器での滞在 (11:00:00 ~ 11:05:14.5)
合計30個のレコードを生成

┌─────────────────────────────────────────┐
│ 連続ペイロード (3個)                     │
│ 開始オフセット: 45.2秒 (random)          │
│                                         │
│ 11:00:45.200  seq=1234  base_payload   │
│ 11:00:45.201  seq=1235  base_payload   │
│ 11:00:45.202  seq=1236  base_payload   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ランダムペイロード (27個)                │
│                                         │
│ 11:00:12.5    seq=789   base_payload   │
│ 11:01:23.8    seq=2341  sub_payload    │
│ 11:02:45.1    seq=156   base_payload   │
│ ...                                     │
│ (滞在時間内にランダムに配置)             │
└─────────────────────────────────────────┘

↓ タイムスタンプでソート

最終出力: 30レコード（時系列順）
```

---

## 実行方法

### 方法1: モジュールとして実行（推奨）

```bash
python -m src2.generator.main
```

### 方法2: 便利スクリプトを使用

```bash
python run_generator.py
```

### 実行結果の例

```
=== シミュレーションデータ生成開始 ===
設定ファイルを読み込み中...
検出器数: 4
シミュレートする通行人数: 10人
各検出器での検出数: 30個
連続ペイロード数: 3個
通行人の移動速度: 1.4 m/s
滞在時間: 180-420秒

シミュレーション実行中...
生成された軌跡数: 10
生成された検出レコード数: 1200

Ground Truth JSONを出力中...
✓ Ground Truth JSON出力完了: src2_result/ground_truth/trajectories.json

検出ログCSVを出力中...
✓ 検出ログCSV出力完了: src2_result/detector_logs/

=== シミュレーションデータ生成完了 ===
```

### 出力ファイルの確認

```bash
# Ground Truth JSON
cat src2_result/ground_truth/trajectories.json

# 検出ログ CSV
head src2_result/detector_logs/A_log.csv
```

---

## 設計の意図

### 1. ドメイン駆動設計 (DDD)

**目的**: ビジネスロジックをドメインモデルとして表現

**実装**:
- `Walker`, `Trajectory`, `Stay` などのドメインモデル
- ビジネスの概念を直接コードに反映
- インフラとの分離

**メリット**:
- コードが仕様書として機能
- ビジネスロジックの変更が容易
- テストしやすい

### 2. 責務の分離

**目的**: 各モジュールが1つの責務のみを持つ

**実装**:
- `walker_generation`: 通行人生成のみ
- `stay_generation`: 滞在生成のみ
- `record_generation`: レコード生成のみ

**メリット**:
- 変更の影響範囲が限定される
- テストが容易
- 理解しやすい

### 3. シンプルさの追求

**Walker からペイロード情報を削除した理由**:

**Before**:
```python
@dataclass
class Walker:
    id: str
    model: str
    assigned_hash_ID: Optional[str]  # モデルAのみ使用
    route: str
```

**問題点**:
- `assigned_hash_ID` はモデルAの時だけ使用
- モデルB/C/Dでは常に `None`
- ドメインモデルが不必要に複雑

**After**:
```python
@dataclass
class Walker:
    id: str
    model: str
    route: str
```

**改善点**:
- すべてのフィールドが全モデルで使用される
- ペイロード決定ロジックは `choose_payload()` に一元化
- ドメインモデルがシンプルに

### 4. 設定ファイルの一元管理

**設計**:
- `json_writer.py` が設定ファイルから直接読み込む
- 呼び出し側が設定情報を知る必要がない

**Before**:
```python
write_ground_truth(
    trajectories,
    num_walkers=settings["num_walkers_to_simulate"],
    num_detectors=len(detectors)
)
```

**After**:
```python
write_ground_truth(trajectories)
```

**メリット**:
- Single Source of Truth
- 呼び出しがシンプル
- 設定変更時の修正箇所が少ない

### 5. 命名規則の統一

**`is_unique` の命名**:

**Before**: `dynamic_unique_payload`
**After**: `is_unique`

**理由**:
- boolean フィールドは `is_*` が慣例
- 短くシンプル
- 疑問形で直感的

### 6. 関数ベースの実装

**設計**: クラスではなく関数を使用

**理由**:
- Pythonらしいシンプルさ
- 依存関係が明確（引数で明示）
- テストしやすい
- 過度な抽象化を避ける

**例**:
```python
# 関数ベース（採用）
def generate_walkers(num_walkers, detectors, ...) -> List[Walker]:
    ...

# クラスベース（不採用）
class WalkerGenerator:
    def __init__(self, detectors, ...):
        ...
    def generate(self, num_walkers) -> List[Walker]:
        ...
```

### 7. 拡張性の確保

**カスタマイズ例**:

```python
# カスタムルート生成アルゴリズム
def my_custom_route_generator(detectors):
    # 入口から出口への最短経路
    return "ABCD"

# simulation.py で関数を差し替え
# walker_generation.generate_random_route = my_custom_route_generator
```

**ポイント**:
- 各関数が独立
- 置き換えが容易
- 段階的な拡張が可能

---

## まとめ

### Generator モジュールの特徴

✅ **レイヤードアーキテクチャ**: Domain / Usecase / Infrastructure の分離
✅ **責務ごとの分割**: 各モジュールが1つの責務のみを持つ
✅ **シンプルな設計**: 不要な複雑さを排除
✅ **関数ベース**: クラスより関数を優先
✅ **型安全**: TypedDict による型定義
✅ **テスタビリティ**: 各関数を独立してテスト可能
✅ **拡張性**: 必要な関数だけ置き換え可能

### ファイル一覧

| ファイル | 行数 | 責務 |
|---------|------|------|
| `domain/walker.py` | 25 | 通行人モデル |
| `domain/trajectory.py` | 30 | 軌跡モデル |
| `domain/stay.py` | 20 | 滞在モデル |
| `domain/detection_record.py` | 25 | 検出レコードモデル |
| `domain/payload_config.py` | 65 | ペイロード設定の型定義 |
| `infrastructure/config_loader.py` | 112 | 設定ファイル読み込み |
| `infrastructure/csv_writer.py` | 78 | CSV出力 |
| `infrastructure/json_writer.py` | 76 | JSON出力 |
| `infrastructure/utils.py` | 20 | 共通ユーティリティ |
| `usecase/walker_generation.py` | 63 | 通行人生成 |
| `usecase/stay_generation.py` | 121 | 滞在リスト生成 |
| `usecase/record_generation.py` | 126 | レコード生成 |
| `usecase/simulation.py` | 97 | シミュレーション実行 |
| `main.py` | 72 | エントリーポイント |
| **合計** | **~900** | |

### 次のステップ

1. **Estimator モジュール**: 検出ログから軌跡を推定
2. **Evaluator モジュール**: Ground Truth と推定結果を比較評価
3. **テストの追加**: ユニットテスト・統合テストの実装
4. **ドキュメント拡充**: API仕様、カスタマイズガイド

---

## 詳細データフロー

このセクションでは、データが生成される過程を関数レベルで詳細に解説します。

### main.py のエントリーポイント

```python
def main():
    # 1. 設定ファイル読み込み
    detectors = load_detectors()
    payload_definitions, model_names, model_probabilities = load_payloads()
    settings = load_simulation_settings()

    # 2. シミュレーション実行
    trajectories, detection_records = simulation.run_simulation(
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities,
        num_walkers=settings["num_walkers_to_simulate"],
        start_time=datetime(2024, 1, 14, 11, 0, 0),
        payloads_per_detector=settings["payloads_per_detector_per_walker"],
        num_consecutive_payloads=settings["num_consecutive_payloads"],
    )

    # 3. 出力
    write_ground_truth(trajectories)
    write_detector_logs(detection_records)
```

**責務**:
- 設定ファイルの読み込み
- シミュレーション実行の起動
- 結果の出力

---

### simulation.run_simulation() の処理

```python
def run_simulation(...):
    # 1. 検出器を辞書に変換（高速アクセスのため）
    detector_dict = {d.id: d for d in detectors}

    # 2. 通行人生成
    walkers = walker_generation.generate_walkers(
        num_walkers=num_walkers,
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities,
    )
    # → [Walker("Walker_1", "Model_C_08", "BADC"), ...]

    trajectories = []
    all_records = []

    # 3. 各通行人について処理
    for i, walker in enumerate(walkers):
        # 3.1 滞在リスト生成
        stays = stay_generation.generate_stays(
            route=walker.route,           # "BADC"
            detectors=detector_dict,      # {A: Detector(...), ...}
            start_time=start_time,        # 2024-01-14 11:00:00
        )
        # → [Stay("B", arrival, departure, duration), ...]

        # 3.2 軌跡オブジェクト作成
        trajectory = Trajectory(
            trajectory_id=f"gt_traj_{i + 1}",  # "gt_traj_1"
            walker_id=walker.id,                # "Walker_1"
            route=walker.route,                 # "BADC"
            stays=stays,                        # 上で生成した滞在リスト
        )
        trajectories.append(trajectory)

        # 3.3 検出レコード生成
        records = record_generation.generate_detection_records(
            walker=walker,
            stays=stays,
            payload_definitions=payload_definitions,
            payloads_per_detector=payloads_per_detector,
            num_consecutive_payloads=num_consecutive_payloads,
        )
        # → [DetectionRecord(timestamp, walker_id, hashed_id, ...), ...]
        all_records.extend(records)

    return trajectories, all_records
```

**責務**:
- 各ユースケースの実行順序を制御
- 結果を集約して返す

---

### walker_generation.generate_walkers() の処理

```python
def generate_walkers(...):
    walkers = []

    for i in range(num_walkers):
        # 1. Walker ID生成
        walker_id = f"Walker_{i + 1}"  # "Walker_1", "Walker_2", ...

        # 2. モデルを確率的に選択
        assigned_model = random.choices(
            model_names,           # ["Model_A", "Model_C_08", ...]
            weights=model_probabilities,  # [0.20, 0.035, ...]
            k=1
        )[0]
        # → "Model_C_08"

        # 3. ランダムなルート生成
        route = generate_random_route(detectors)
        # → "BADC" (検出器IDをシャッフル)

        # 4. Walker オブジェクト作成
        walkers.append(Walker(
            id=walker_id,
            model=assigned_model,
            route=route,
        ))

    return walkers
```

**責務**:
- 通行人の生成（ID、モデル、ルート）
- ルートはランダムに決定

**具体例**:
```python
Walker(
    id="Walker_1",
    model="Model_C_08",
    route="BADC"
)
```

---

### stay_generation.generate_stays() の処理

```python
def generate_stays(route, detectors, start_time):
    # 1. 設定ファイルから数値パラメータを読み込む
    settings = load_simulation_settings()
    stay_duration_min = settings["stay_duration_min_seconds"]  # 180
    stay_duration_max = settings["stay_duration_max_seconds"]  # 420
    walker_speed = settings["walker_speed"]                    # 1.4
    variation_factor = settings["variation_factor"]            # 0.1

    stays = []
    current_time = start_time  # 2024-01-14 11:00:00

    # 2. ルート上の検出器を順に処理
    route_detectors = [detectors[detector_id] for detector_id in route]
    # route="BADC" → [Detector("B"), Detector("A"), ...]

    for i, detector in enumerate(route_detectors):
        # 2.1 到着時刻
        arrival_time = current_time

        # 2.2 滞在時間をランダムに決定
        stay_duration = random.uniform(stay_duration_min, stay_duration_max)
        # → 314.5秒（ランダム）

        departure_time = arrival_time + timedelta(seconds=stay_duration)

        # 2.3 Stay オブジェクト作成
        stays.append(Stay(
            detector_id=detector.id,
            arrival_time=arrival_time,
            departure_time=departure_time,
            duration_seconds=stay_duration,
        ))

        # 2.4 次の検出器への移動時間を計算
        if i < len(route_detectors) - 1:
            next_detector = route_detectors[i + 1]

            # 距離を計算
            distance = sqrt(
                (next_detector.x - detector.x) ** 2 +
                (next_detector.y - detector.y) ** 2
            )

            # 移動時間 = 距離 / 速度 + ランダムなばらつき
            base_time = distance / walker_speed
            variation = base_time * variation_factor * (random.random() * 2 - 1)
            travel_duration = max(0, base_time + variation)

            # 次の到着時刻 = 出発時刻 + 移動時間
            current_time = departure_time + timedelta(seconds=travel_duration)

    return stays
```

**責務**:
- 各検出器での滞在情報を生成
- 移動時間を考慮して到着時刻を計算
- 設定ファイルから数値パラメータを自動読み込み

**具体例**:
```python
[
    Stay(
        detector_id="B",
        arrival_time=datetime(2024, 1, 14, 11, 0, 0),
        departure_time=datetime(2024, 1, 14, 11, 6, 41),
        duration_seconds=401.12
    ),
    Stay(
        detector_id="A",
        arrival_time=datetime(2024, 1, 14, 14, 49, 8),
        departure_time=datetime(2024, 1, 14, 14, 55, 52),
        duration_seconds=404.25
    ),
    # ... 続く
]
```

---

### record_generation.generate_detection_records() の処理

```python
def generate_detection_records(walker, stays, payload_definitions,
                                payloads_per_detector, num_consecutive_payloads):
    records = []

    # 各滞在について処理
    for stay in stays:
        stay_records = []

        # 1. 連続ペイロードの生成
        if num_consecutive_payloads > 0:
            # 連続ペイロードの開始オフセットを決定
            max_offset = stay.duration_seconds - (num_consecutive_payloads * 0.001)
            consecutive_start_offset = random.uniform(0, max(0, max_offset))

            # 開始シーケンス番号
            current_sequence_number = random.randint(0, 4095)

            # 連続ペイロード（1ms間隔）
            for k in range(num_consecutive_payloads):
                record_time = (
                    stay.arrival_time
                    + timedelta(seconds=consecutive_start_offset)
                    + timedelta(milliseconds=k)
                )

                # ペイロード選択
                chosen_payload = choose_payload(
                    walker.id, walker.model, payload_definitions
                )

                stay_records.append(DetectionRecord(
                    timestamp=record_time,
                    walker_id=walker.id,
                    hashed_id=chosen_payload,
                    detector_id=stay.detector_id,
                    sequence_number=current_sequence_number,
                ))

                current_sequence_number = (current_sequence_number + 1) % 4096

        # 2. ランダムペイロードの生成
        num_random_payloads = payloads_per_detector - num_consecutive_payloads
        for _ in range(num_random_payloads):
            # 滞在時間内のランダムな時刻
            offset_seconds = random.uniform(0, stay.duration_seconds)
            record_time = stay.arrival_time + timedelta(seconds=offset_seconds)

            # ペイロード選択
            chosen_payload = choose_payload(
                walker.id, walker.model, payload_definitions
            )

            random_sequence_number = random.randint(0, 4095)

            stay_records.append(DetectionRecord(
                timestamp=record_time,
                walker_id=walker.id,
                hashed_id=chosen_payload,
                detector_id=stay.detector_id,
                sequence_number=random_sequence_number,
            ))

        # 3. タイムスタンプでソート
        stay_records.sort(key=lambda r: r.timestamp)
        records.extend(stay_records)

    return records
```

**責務**:
- 滞在期間中の検出レコードを生成
- 連続ペイロード（シーケンス番号連続）とランダムペイロードを生成
- ペイロード選択ロジックを適用

**ペイロード選択ロジック**:
```python
def choose_payload(walker_id, model_name, payload_definitions):
    # ユニーク型モデル
    if payload_definitions[model_name]["is_unique"]:
        return f"unique_and_hashed_payload_{walker_id}"

    # その他のモデル
    distribution = payload_definitions[model_name]["payload_distribution"]
    payload_types = list(distribution.keys())
    probabilities = list(distribution.values())
    return random.choices(payload_types, weights=probabilities, k=1)[0]
```

**具体例（Model_C_08の場合）**:
```python
[
    DetectionRecord(
        timestamp=datetime(2024, 1, 14, 11, 0, 45, 200000),
        walker_id="Walker_1",
        hashed_id="C_08_base_payload",  # 90%の確率
        detector_id="B",
        sequence_number=1234
    ),
    DetectionRecord(
        timestamp=datetime(2024, 1, 14, 11, 0, 45, 201000),
        walker_id="Walker_1",
        hashed_id="C_08_base_payload",
        detector_id="B",
        sequence_number=1235  # 連続
    ),
    # ... 続く
]
```

---

### 出力処理

#### json_writer.write_ground_truth(trajectories)

```python
def write_ground_truth(trajectories):
    # 1. 設定ファイルから情報を読み込み
    detectors = load_detectors()
    simulation_settings = load_simulation_settings()

    # 2. メタデータ作成
    metadata = {
        "generation_timestamp": format_timestamp(datetime.now()),
        "num_walkers": simulation_settings["num_walkers_to_simulate"],
        "num_detectors": len(detectors),
        "num_trajectories": len(trajectories),
    }

    # 3. 軌跡データを辞書に変換
    trajectory_list = []
    for traj in trajectories:
        trajectory_list.append({
            "trajectory_id": traj.trajectory_id,
            "walker_id": traj.walker_id,
            "route": traj.route,
            "stays": [
                {
                    "detector_id": stay.detector_id,
                    "arrival_time": format_timestamp(stay.arrival_time),
                    "departure_time": format_timestamp(stay.departure_time),
                    "duration_seconds": stay.duration_seconds,
                }
                for stay in traj.stays
            ],
        })

    # 4. JSON出力
    output_data = {"metadata": metadata, "trajectories": trajectory_list}
    with open("src2_result/ground_truth/trajectories.json", "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
```

**責務**:
- `Trajectory`オブジェクトをJSON形式に変換
- メタデータを自動生成
- ファイルに書き込み

#### csv_writer.write_detector_logs(records)

```python
def write_detector_logs(records):
    # 1. 検出器ごとにレコードを分類
    detector_records = {}
    for record in records:
        detector_id = record.detector_id
        if detector_id not in detector_records:
            detector_records[detector_id] = []
        detector_records[detector_id].append(record)

    # 2. 各検出器のCSVファイルを作成
    for detector_id, detector_records_list in detector_records.items():
        # タイムスタンプでソート
        detector_records_list.sort(key=lambda r: r.timestamp)

        # CSVファイルに書き込み
        filepath = f"src2_result/detector_logs/{detector_id}_log.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Walker_ID", "Hashed_Payload",
                "Detector_ID", "Sequence_Number"
            ])

            for record in detector_records_list:
                writer.writerow([
                    format_timestamp(record.timestamp),
                    record.walker_id,
                    record.hashed_id,
                    record.detector_id,
                    record.sequence_number,
                ])
```

**責務**:
- 検出レコードを検出器ごとに分類
- CSV形式でファイルに書き込み
- タイムスタンプでソート

---

### データフロー全体のまとめ

```
main.py
  ├─ 設定読み込み
  │   ├─ load_detectors()
  │   ├─ load_payloads()
  │   └─ load_simulation_settings()
  │
  ├─ シミュレーション実行
  │   └─ simulation.run_simulation()
  │       │
  │       ├─ walker_generation.generate_walkers()
  │       │   ├─ for each walker:
  │       │   │   ├─ ID生成
  │       │   │   ├─ モデル選択（確率的）
  │       │   │   └─ ルート生成（ランダム）
  │       │   └─ return List[Walker]
  │       │
  │       └─ for each walker:
  │           │
  │           ├─ stay_generation.generate_stays()
  │           │   ├─ load_simulation_settings()  # 設定読み込み
  │           │   ├─ for each detector in route:
  │           │   │   ├─ 滞在時間決定（ランダム）
  │           │   │   ├─ Stay作成
  │           │   │   └─ 移動時間計算
  │           │   └─ return List[Stay]
  │           │
  │           ├─ Trajectory作成
  │           │   └─ Trajectory(id, walker_id, route, stays)
  │           │
  │           └─ record_generation.generate_detection_records()
  │               ├─ for each stay:
  │               │   ├─ 連続ペイロード生成
  │               │   │   └─ choose_payload()
  │               │   └─ ランダムペイロード生成
  │               │       └─ choose_payload()
  │               └─ return List[DetectionRecord]
  │
  └─ 出力
      ├─ write_ground_truth(trajectories)
      │   └─ src2_result/ground_truth/trajectories.json
      │
      └─ write_detector_logs(records)
          └─ src2_result/detector_logs/{A,B,C,D}_log.csv
```

---

**ドキュメント作成日**: 2025-12-08
**最終更新日**: 2025-12-08
**バージョン**: 2.0
