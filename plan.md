# シミュレーター再設計要件定義書

## プロジェクト概要

スマートフォン検出による人流追跡シミュレーターを、Generator・Estimator・Evaluatorの3層アーキテクチャに再設計する。

## ディレクトリ構造

```
src2/                          # 新規実装ディレクトリ (既存のsrc/は保持)
├── generator/                 # データ生成モジュール
│   ├── domain/               # ドメインモデル
│   │   ├── __init__.py
│   │   ├── detector.py       # 検出器
│   │   ├── walker.py         # 通行人
│   │   ├── stay.py           # 滞在情報
│   │   ├── trajectory.py     # 軌跡
│   │   └── detection_record.py  # 検出レコード
│   ├── usecase/              # ビジネスロジック
│   │   ├── __init__.py
│   │   └── generate_simulation.py
│   ├── infrastructure/        # データ永続化
│   │   ├── __init__.py
│   │   ├── config_loader.py
│   │   ├── csv_writer.py
│   │   └── json_writer.py
│   └── main.py               # エントリーポイント
│
├── estimator/                # 経路推定モジュール
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── detection_record.py
│   │   ├── estimated_stay.py
│   │   └── estimated_trajectory.py
│   ├── usecase/
│   │   ├── __init__.py
│   │   └── estimate_trajectories.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── csv_reader.py
│   │   └── json_writer.py
│   └── main.py
│
├── evaluator/                # 評価モジュール
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── trajectory.py
│   │   ├── trajectory_match.py
│   │   └── evaluation_result.py
│   ├── usecase/
│   │   ├── __init__.py
│   │   └── evaluate_trajectories.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── json_reader.py
│   └── main.py
│
└── shared/                   # 共通モジュール
    ├── __init__.py
    ├── domain/
    │   ├── __init__.py
    │   ├── detector.py       # 共通の検出器型
    │   └── base_types.py     # 基底クラス
    └── utils/
        ├── __init__.py
        ├── datetime_utils.py
        └── distance_calculator.py

config/                       # 設定ファイル (既存)
├── detectors.jsonc
├── payloads.jsonc
├── simulation_settings.jsonc
└── evaluation_settings.jsonc  # 新規追加

result/                       # 出力ディレクトリ (既存を拡張)
├── detector_logs/            # 検出ログCSV
├── ground_truth/             # Ground Truth JSON (新規)
│   └── trajectories.json
├── estimated/                # 推定結果JSON (新規)
│   └── trajectories.json
└── evaluation/               # 評価結果JSON (新規)
    └── results.json
```

---

## 1. Generator (データ生成モジュール)

### 目的
シミュレーションデータと Ground Truth を生成する。

### ドメインモデル

#### `domain/detector.py`
```python
from dataclasses import dataclass

@dataclass
class Detector:
    """検出器"""
    id: str          # 例: "A", "B", "C", "D"
    x: float
    y: float
```

#### `domain/walker.py`
```python
from dataclasses import dataclass

@dataclass
class Walker:
    """通行人"""
    id: str                    # 例: "Walker_1"
    model: str                 # 例: "iPhone_15"
    assigned_payload: str      # 例: "C_01_base_payload"
    route_string: str          # 例: "ABCD"
```

#### `domain/stay.py`
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Stay:
    """1つの検出器での滞在"""
    detector_id: str
    arrival_time: datetime
    departure_time: datetime
    duration_seconds: float
```

#### `domain/trajectory.py`
```python
from dataclasses import dataclass
from typing import List
from .stay import Stay

@dataclass
class Trajectory:
    """1つの軌跡 (Ground Truth)"""
    trajectory_id: str         # 例: "gt_traj_1"
    walker_ids: List[str]      # 例: ["Walker_1"]
    route_string: str          # 例: "ABCD"
    timeline: List[Stay]
```

#### `domain/detection_record.py`
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DetectionRecord:
    """検出レコード (ログに記録される1行)"""
    timestamp: datetime
    walker_id: str             # Ground Truth用 (実運用では存在しない)
    hashed_payload: str
    detector_id: str
    sequence_number: int
```

### 入力

#### `config/detectors.jsonc`
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

#### `config/payloads.jsonc` (既存)
維持

#### `config/simulation_settings.jsonc`
```jsonc
{
  "simulation_settings": {
    "num_walkers_to_simulate": 10,
    "payloads_per_detector_per_walker": 30,
    "num_consecutive_payloads": 3,
    "walker_speed": 1.4,
    "variation_factor": 0.1,
    "stay_duration_min_seconds": 180,    // 新規追加: 滞在時間の最小値
    "stay_duration_max_seconds": 420     // 新規追加: 滞在時間の最大値
  }
}
```

### 出力

#### `result/detector_logs/*.csv`

**ファイル名**: `A_log.csv`, `B_log.csv`, `C_log.csv`, `D_log.csv`

**フォーマット**:
```csv
Timestamp,Walker_ID,Hashed_Payload,Detector_ID,Sequence_Number
2024-01-14 11:00:05.123,Walker_1,C_01_base_payload,A,100
2024-01-14 11:00:15.456,Walker_1,C_01_base_payload,A,101
2024-01-14 11:01:23.789,Walker_2,C_02_base_payload,A,200
```

**注意**:
- タイムスタンプはミリ秒まで記録 (`YYYY-MM-DD HH:MM:SS.mmm`)
- 各検出器ごとに1つのCSVファイル
- 検出器座標は含めない (設定ファイルで一元管理)

#### `result/ground_truth/trajectories.json`

```json
{
  "metadata": {
    "generation_timestamp": "2024-12-07 15:00:00",
    "num_walkers": 10,
    "num_detectors": 4,
    "num_trajectories": 10
  },
  "trajectories": [
    {
      "trajectory_id": "gt_traj_1",
      "walker_ids": ["Walker_1"],
      "route_string": "ABCD",
      "timeline": [
        {
          "detector_id": "A",
          "arrival_time": "2024-01-14 11:00:00.000",
          "departure_time": "2024-01-14 11:05:00.000",
          "duration_seconds": 300.0
        },
        {
          "detector_id": "B",
          "arrival_time": "2024-01-14 11:05:30.000",
          "departure_time": "2024-01-14 11:11:00.000",
          "duration_seconds": 330.0
        },
        {
          "detector_id": "C",
          "arrival_time": "2024-01-14 11:13:00.000",
          "departure_time": "2024-01-14 11:18:00.000",
          "duration_seconds": 300.0
        },
        {
          "detector_id": "D",
          "arrival_time": "2024-01-14 11:19:00.000",
          "departure_time": "2024-01-14 11:24:00.000",
          "duration_seconds": 300.0
        }
      ]
    }
  ]
}
```

**重要**:
- 軌跡パターンは事前に定義しない
- 各軌跡を独立したオブジェクトとして保存
- 時間情報を含めてすべて記録
- パターン化や集計は評価時に行う

### 主要ロジック

#### 滞在時間の決定
```python
# usecase/generate_simulation.py内
for detector in route_detectors:
    arrival_time = current_time

    # 滞在時間を明示的に決定 (設定ファイルから範囲を読み込む)
    stay_duration = random.uniform(
        config.stay_duration_min_seconds,
        config.stay_duration_max_seconds
    )
    departure_time = arrival_time + timedelta(seconds=stay_duration)

    # この滞在期間中にレコードを生成
    # レコードは arrival_time ~ departure_time の範囲内でランダムに配置
```

---

## 2. Estimator (経路推定モジュール)

### 目的
検出ログから軌跡を推定する。

### ドメインモデル

#### `domain/detection_record.py`
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DetectionRecord:
    """検出ログから読み込んだレコード"""
    timestamp: datetime
    walker_id: str             # Estimatorでは使用しない (Ground Truth情報)
    hashed_payload: str
    detector_id: str
    sequence_number: int
    is_judged: bool = False    # クラスタリング処理で使用
```

#### `domain/estimated_stay.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List
from .detection_record import DetectionRecord

@dataclass
class EstimatedStay:
    """推定された1つの検出器での滞在"""
    detector_id: str
    detections: List[DetectionRecord]      # この滞在中の全検出
    first_detection: datetime
    last_detection: datetime
    estimated_arrival: datetime
    estimated_departure: datetime
    estimated_duration_seconds: float
    num_detections: int
```

#### `domain/estimated_trajectory.py`
```python
from dataclasses import dataclass
from typing import List
from .estimated_stay import EstimatedStay

@dataclass
class EstimatedTrajectory:
    """推定された1つの軌跡"""
    trajectory_id: str                     # 例: "est_traj_1"
    cluster_ids: List[str]                 # 例: ["cluster_1"]
    route_string: str                      # 例: "ABCD"
    timeline: List[EstimatedStay]
```

### 入力

- `config/detectors.jsonc`
- `result/detector_logs/*.csv`

### 出力

#### `result/estimated/trajectories.json`

```json
{
  "metadata": {
    "estimation_timestamp": "2024-12-07 15:30:00",
    "num_clusters": 11,
    "num_trajectories": 11,
    "estimation_method": "window_max"
  },
  "trajectories": [
    {
      "trajectory_id": "est_traj_1",
      "cluster_ids": ["cluster_1"],
      "route_string": "ABCD",
      "timeline": [
        {
          "detector_id": "A",
          "detections": [
            {
              "timestamp": "2024-01-14 11:00:05.123",
              "hashed_payload": "C_01_base_payload",
              "sequence_number": 100,
              "is_judged": true
            }
          ],
          "first_detection": "2024-01-14 11:00:05.123",
          "last_detection": "2024-01-14 11:04:55.789",
          "estimated_arrival": "2024-01-14 11:00:00.000",
          "estimated_departure": "2024-01-14 11:05:00.000",
          "estimated_duration_seconds": 300.0,
          "num_detections": 21
        }
      ]
    }
  ]
}
```

### 推定ロジック (現時点では実装しない)

**注意**: Estimatorの推定ロジックは後で再設計するため、現時点では**スタブ実装**とする。

```python
# usecase/estimate_trajectories.py
def estimate_trajectories(detection_logs):
    """
    TODO: 推定ロジックは後で実装
    現時点ではダミーデータを返す
    """
    return []
```

---

## 3. Evaluator (評価モジュール)

### 目的
Ground Truthと推定結果を比較して評価する。

### ドメインモデル

#### `domain/trajectory.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Stay:
    """滞在情報 (評価用の統一インターフェース)"""
    detector_id: str
    arrival_time: datetime
    departure_time: datetime
    duration_seconds: float

@dataclass
class Trajectory:
    """軌跡 (評価用の統一インターフェース)"""
    trajectory_id: str
    route_string: str
    timeline: List[Stay]
```

#### `domain/trajectory_match.py`
```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class TrajectoryMatch:
    """2つの軌跡のマッチング結果"""
    ground_truth_id: str
    estimated_id: str
    similarity_score: float        # 0.0 ~ 1.0
    temporal_errors: Dict[str, Dict[str, float]]  # detector_id → {arrival_error, departure_error, duration_error}
```

#### `domain/evaluation_result.py`
```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EvaluationResult:
    """評価結果"""
    metadata: Dict
    overall_metrics: Dict
    matched_pairs: List[TrajectoryMatch]
    unmatched_ground_truth: List[str]
    unmatched_estimated: List[str]
```

### 入力

- `result/ground_truth/trajectories.json`
- `result/estimated/trajectories.json`
- `config/evaluation_settings.jsonc` (新規作成)

#### `config/evaluation_settings.jsonc`

```jsonc
{
  "evaluation_settings": {
    "matching_method": "dtw",           // "dtw", "euclidean", "threshold"
    "time_threshold_seconds": 300,      // 閾値ベースマッチングの場合の時間閾値
    "dtw_weight_time": 1.0,             // DTWの時間重み
    "dtw_weight_location": 10.0,        // DTWの位置重み (異なる検出器は大きなペナルティ)
    "clustering_method": "hierarchical" // 将来的な拡張用
  }
}
```

### 出力

#### `result/evaluation/results.json`

```json
{
  "metadata": {
    "evaluation_timestamp": "2024-12-07 16:00:00",
    "ground_truth_file": "result/ground_truth/trajectories.json",
    "estimated_file": "result/estimated/trajectories.json",
    "evaluation_method": "dtw",
    "num_ground_truth_trajectories": 10,
    "num_estimated_trajectories": 11
  },
  "overall_metrics": {
    "num_matched_pairs": 9,
    "num_unmatched_ground_truth": 1,
    "num_unmatched_estimated": 2,
    "avg_similarity_score": 0.87,
    "avg_temporal_error_seconds": 3.5,
    "precision": 0.818,
    "recall": 0.9,
    "f1_score": 0.857
  },
  "matched_pairs": [
    {
      "ground_truth_id": "gt_traj_1",
      "estimated_id": "est_traj_1",
      "similarity_score": 0.95,
      "temporal_errors": {
        "A": {
          "arrival_error_seconds": 5.0,
          "departure_error_seconds": 0.0,
          "duration_error_seconds": 5.0
        },
        "B": {
          "arrival_error_seconds": 5.0,
          "departure_error_seconds": 0.0,
          "duration_error_seconds": 5.0
        }
      }
    }
  ],
  "unmatched_ground_truth": ["gt_traj_3"],
  "unmatched_estimated": ["est_traj_10", "est_traj_11"]
}
```

### 評価ロジック

#### マッチング戦略

評価時に軌跡の類似度を計算してマッチングを行う。

```python
# usecase/evaluate_trajectories.py

def evaluate(ground_truth_trajectories, estimated_trajectories, config):
    """
    1. 類似度行列を構築
    2. Hungarian Algorithmでマッチング
    3. 各ペアの時間誤差を計算
    4. 全体指標を計算
    """
    # Step 1: 類似度行列
    similarity_matrix = calculate_similarity_matrix(
        ground_truth_trajectories,
        estimated_trajectories,
        method=config.matching_method
    )

    # Step 2: マッチング
    matched_pairs = hungarian_algorithm(similarity_matrix)

    # Step 3: 時間誤差計算
    for (gt_id, est_id) in matched_pairs:
        temporal_errors = calculate_temporal_errors(gt_id, est_id)

    # Step 4: 全体指標
    precision = num_matched / num_estimated
    recall = num_matched / num_ground_truth
    f1 = 2 * precision * recall / (precision + recall)

    return EvaluationResult(...)
```

#### 類似度計算 (DTWベース)

```python
def calculate_dtw_distance(traj1, traj2):
    """
    Dynamic Time Warping距離を計算

    コスト定義:
    - 同じ検出器: 時間差の絶対値
    - 異なる検出器: 大きなペナルティ (例: 10000秒相当)
    """
    # DTW実装
    # ...
    return dtw_distance
```

---

## 4. Shared (共通モジュール)

### `shared/domain/detector.py`
```python
from dataclasses import dataclass

@dataclass
class Detector:
    """検出器 (全モジュールで共通)"""
    id: str
    x: float
    y: float
```

### `shared/domain/base_types.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class BaseStay:
    """滞在の基底クラス"""
    detector_id: str
    arrival_time: datetime
    departure_time: datetime
    duration_seconds: float

@dataclass
class BaseTrajectory:
    """軌跡の基底クラス"""
    trajectory_id: str
    route_string: str
```

### `shared/utils/distance_calculator.py`
```python
import math
from ..domain.detector import Detector

def calculate_euclidean_distance(det1: Detector, det2: Detector) -> float:
    """2つの検出器間のユークリッド距離を計算"""
    return math.sqrt((det2.x - det1.x) ** 2 + (det2.y - det1.y) ** 2)

def calculate_min_travel_time(det1: Detector, det2: Detector, speed: float) -> float:
    """検出器間の最小移動時間を計算"""
    distance = calculate_euclidean_distance(det1, det2)
    return distance / speed if speed > 0 else 0
```

### `shared/utils/datetime_utils.py`
```python
from datetime import datetime

def format_timestamp(dt: datetime) -> str:
    """タイムスタンプをミリ秒まで出力 (YYYY-MM-DD HH:MM:SS.mmm)"""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def parse_timestamp(ts_str: str) -> datetime:
    """タイムスタンプ文字列をパース"""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
```

---

## 5. 実装の優先順位

### Phase 1: 基盤構築 (最優先)

1. ✅ ディレクトリ構造の作成
2. ✅ Shared モジュールの実装
3. ✅ 各モジュールのドメインモデル定義

### Phase 2: Generator実装

1. ✅ config読み込み機能
2. ✅ Walker生成ロジック
3. ✅ 滞在時間の明示的決定
4. ✅ 検出レコード生成
5. ✅ CSV/JSON出力

### Phase 3: Estimator実装 (スタブ)

1. ✅ CSV読み込み機能
2. ⏸️ 推定ロジック (後回し、現時点ではスタブ)
3. ✅ JSON出力

### Phase 4: Evaluator実装

1. ✅ JSON読み込み機能
2. ✅ 類似度計算 (DTW実装)
3. ✅ マッチングアルゴリズム (Hungarian)
4. ✅ 評価指標計算
5. ✅ JSON出力

---

## 6. 技術的要件

### Python バージョン
- Python 3.10以上

### 必要なライブラリ
```
dataclasses  (標準ライブラリ)
datetime     (標準ライブラリ)
json         (標準ライブラリ)
csv          (標準ライブラリ)
numpy        (DTW計算用)
scipy        (Hungarian Algorithm用)
```

### コーディング規約
- Type hintsを使用
- Dataclassを活用
- JSONCファイルはコメント除去してパース
- タイムスタンプはミリ秒まで記録

---

## 7. テスト要件

### 最小限のテストケース

#### Generator
- 10人のウォーカーを生成
- 各ウォーカーが4つの検出器を訪問
- Ground Truth JSONの生成確認

#### Estimator (スタブ)
- CSVファイルの読み込み確認
- 空の推定結果JSONを出力

#### Evaluator
- 同一の軌跡をマッチングできる
- 時間誤差を正しく計算できる

---

## 8. 既存コードとの関係

- **既存**: `src/` ディレクトリは保持 (削除しない)
- **新規**: `src2/` ディレクトリに新実装
- **共通**: `config/` と `result/` は共有 (ただし出力先サブディレクトリは分離)

---

## 9. 設計原則

### データの記録と評価の分離

**重要**: Generator と Estimator は**生データをそのまま保存**する。

- ❌ パターン化や集計をしない
- ❌ 事前に軌跡をグループ化しない
- ✅ 各軌跡を独立したオブジェクトとして記録
- ✅ 時間情報を含めてすべて保存

**評価時にパターン判定を行う**:
- Evaluatorが評価戦略に応じて軌跡をグループ化・マッチング
- 同じデータで異なる評価手法を試せる

### 人数推定精度に焦点

- ✅ 各軌跡パターンの人数を正しく推定できたか
- ✅ 時間的な精度 (到着・出発・滞在時間の誤差)
- ⏸️ 個人追跡精度は後回し (将来的に追加可能)

---

## 10. 実装時の注意点

### Generator
- 滞在時間を**明示的に決定**してから検出レコードを生成
- 検出レコードは滞在期間内にランダムに配置
- 検出器座標は出力に含めない (detectors.jsonc で一元管理)

### Estimator
- 推定ロジックは後で再設計するため、現時点ではスタブ実装
- 入力CSVの読み込みと出力JSONの書き込みのみ実装
- `estimated_arrival`, `estimated_departure` の推定方法は未定 (TODO)

### Evaluator
- 軌跡の類似度計算にDTWを使用
- マッチングにHungarian Algorithmを使用
- 評価設定 (`evaluation_settings.jsonc`) でパラメータを変更可能

---

## 11. 実装完了の定義

以下が完了したら Phase 1-2 完了とする:

- [ ] ディレクトリ構造の作成
- [ ] Shared モジュールの実装
- [ ] Generator の完全実装
- [ ] Estimator のスタブ実装
- [ ] Evaluator の完全実装
- [ ] 10人のウォーカーでエンドツーエンドテストが成功
- [ ] 評価結果JSONが出力される

---

## 付録: データフロー図

```
[config/detectors.jsonc]
[config/payloads.jsonc]
[config/simulation_settings.jsonc]
         ↓
    [Generator]
         ↓
    ┌────┴────┐
    ↓         ↓
[detector_logs/*.csv]  [ground_truth/trajectories.json]
    ↓                              ↓
[Estimator]                        ↓
    ↓                              ↓
[estimated/trajectories.json]      ↓
    ↓                              ↓
    └──────────┬───────────────────┘
               ↓
          [Evaluator]
               ↓
    [evaluation/results.json]
```

---

以上
