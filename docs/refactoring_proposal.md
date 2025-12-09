# Generator リファクタリング提案

## 現在の問題点

### 1. 単一責任の原則違反
`generate_simulation.py` が複数の責務を持つ：
- 通行人生成
- タイムライン生成
- 検出レコード生成
- 全体のオーケストレーション

### 2. テスタビリティの欠如
- 各機能を個別にテストできない
- モック化が困難
- 依存関係がハードコード

### 3. 拡張性の低さ
- 異なる生成アルゴリズムへの切り替えが困難
- カスタマイズポイントが不明確

## 提案する構造

```
src2/generator/
├── domain/           # ドメインモデル（変更なし）
│   ├── walker.py
│   ├── trajectory.py
│   └── ...
│
├── usecase/
│   ├── services/     # 責務ごとのサービスクラス（新規）
│   │   ├── __init__.py
│   │   ├── walker_generation_service.py
│   │   ├── timeline_generation_service.py
│   │   └── record_generation_service.py
│   │
│   ├── simulation_service.py  # メインオーケストレーター（新規）
│   └── generate_simulation.py # 後方互換用（削除候補）
│
├── infrastructure/   # インフラ層（変更なし）
│   └── ...
│
└── main.py          # エントリーポイント（依存性注入を実装）
```

## サービス責務分割

### 1. WalkerGenerationService
**責務**: 通行人の生成とモデル割り当て

```python
class WalkerGenerationService:
    def __init__(
        self,
        detectors: List[Detector],
        payload_definitions: PayloadDefinitionsDict,
        model_names: List[str],
        model_probabilities: List[float]
    ):
        self.detectors = detectors
        self.payload_definitions = payload_definitions
        self.model_names = model_names
        self.model_probabilities = model_probabilities

    def generate_walkers(self, num_walkers: int) -> List[Walker]:
        """N人の通行人を生成"""

    def generate_random_route(self) -> str:
        """ランダムなルートを生成"""
```

**メリット**:
- ルート生成アルゴリズムを変更可能
- モデル選択ロジックをカスタマイズ可能
- テストが容易

### 2. TimelineGenerationService
**責務**: 滞在タイムラインの生成

```python
class TimelineGenerationService:
    def __init__(
        self,
        detectors: Dict[str, Detector],
        start_time: datetime,
        stay_duration_min: float,
        stay_duration_max: float,
        walker_speed: float,
        variation_factor: float
    ):
        self.detectors = detectors
        self.start_time = start_time
        self.stay_duration_min = stay_duration_min
        self.stay_duration_max = stay_duration_max
        self.walker_speed = walker_speed
        self.variation_factor = variation_factor

    def generate_timeline(self, route: str) -> List[Stay]:
        """ルートに基づいてタイムラインを生成"""

    def calculate_travel_time(
        self,
        from_detector: Detector,
        to_detector: Detector
    ) -> float:
        """移動時間を計算"""
```

**メリット**:
- 滞在時間分布を変更可能（一様分布 → 正規分布など）
- 移動モデルをカスタマイズ可能
- 時間計算ロジックを独立してテスト可能

### 3. RecordGenerationService
**責務**: 検出レコードの生成

```python
class RecordGenerationService:
    def __init__(
        self,
        payload_definitions: PayloadDefinitionsDict,
        payloads_per_detector: int,
        num_consecutive_payloads: int
    ):
        self.payload_definitions = payload_definitions
        self.payloads_per_detector = payloads_per_detector
        self.num_consecutive_payloads = num_consecutive_payloads

    def generate_records(
        self,
        walker: Walker,
        timeline: List[Stay]
    ) -> List[DetectionRecord]:
        """滞在タイムラインからレコードを生成"""

    def choose_payload(
        self,
        model_name: str,
        assigned_hash_ID: str | None
    ) -> str:
        """ペイロードを選択"""
```

**メリット**:
- レコード生成パターンを変更可能
- ペイロード選択アルゴリズムをカスタマイズ可能
- 連続/ランダムの比率を柔軟に設定可能

### 4. SimulationService (オーケストレーター)
**責務**: 全体の調整

```python
class SimulationService:
    def __init__(
        self,
        walker_service: WalkerGenerationService,
        timeline_service: TimelineGenerationService,
        record_service: RecordGenerationService
    ):
        self.walker_service = walker_service
        self.timeline_service = timeline_service
        self.record_service = record_service

    def run_simulation(
        self,
        num_walkers: int
    ) -> Tuple[List[Trajectory], List[DetectionRecord]]:
        """シミュレーション全体を実行"""
        # 1. 通行人生成
        walkers = self.walker_service.generate_walkers(num_walkers)

        # 2. 各通行人の軌跡とレコード生成
        trajectories = []
        all_records = []

        for i, walker in enumerate(walkers):
            # タイムライン生成
            timeline = self.timeline_service.generate_timeline(walker.route)

            # 軌跡作成
            trajectory = Trajectory(
                trajectory_id=f"gt_traj_{i + 1}",
                walker_id=walker.id,
                route=walker.route,
                timeline=timeline
            )
            trajectories.append(trajectory)

            # レコード生成
            records = self.record_service.generate_records(walker, timeline)
            all_records.extend(records)

        return trajectories, all_records
```

**メリット**:
- 高レベルのフローが明確
- 各サービスの呼び出し順序を管理
- 依存性注入により各サービスを差し替え可能

## main.py での依存性注入

```python
def main():
    # 設定読み込み
    detectors = load_detectors()
    payload_definitions, model_names, model_probabilities = load_payloads()
    settings = load_simulation_settings()

    # サービスのインスタンス化（依存性注入）
    walker_service = WalkerGenerationService(
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities
    )

    timeline_service = TimelineGenerationService(
        detectors={d.id: d for d in detectors},
        start_time=datetime(2024, 1, 14, 11, 0, 0),
        stay_duration_min=settings["stay_duration_min_seconds"],
        stay_duration_max=settings["stay_duration_max_seconds"],
        walker_speed=settings["walker_speed"],
        variation_factor=settings["variation_factor"]
    )

    record_service = RecordGenerationService(
        payload_definitions=payload_definitions,
        payloads_per_detector=settings["payloads_per_detector_per_walker"],
        num_consecutive_payloads=settings["num_consecutive_payloads"]
    )

    # オーケストレーターの作成
    simulation = SimulationService(
        walker_service=walker_service,
        timeline_service=timeline_service,
        record_service=record_service
    )

    # シミュレーション実行
    trajectories, records = simulation.run_simulation(
        num_walkers=settings["num_walkers_to_simulate"]
    )

    # 出力
    write_ground_truth(trajectories)
    write_detector_logs(records)
```

## メリット

### 1. 単一責任の原則
各クラスが1つの責務のみを持つ

### 2. テスタビリティ
```python
# 個別のサービスをテスト可能
def test_walker_generation():
    service = WalkerGenerationService(
        detectors=mock_detectors,
        payload_definitions=mock_payloads,
        model_names=["Model_A"],
        model_probabilities=[1.0]
    )
    walkers = service.generate_walkers(10)
    assert len(walkers) == 10
```

### 3. 拡張性
```python
# カスタムルート生成アルゴリズムへの差し替え
class CustomWalkerGenerationService(WalkerGenerationService):
    def generate_random_route(self) -> str:
        # カスタムロジック
        return "ABC"  # 固定ルート

# 使用
walker_service = CustomWalkerGenerationService(...)
```

### 4. 依存性の明確化
- コンストラクタで必要な依存を明示
- 実行時の動的な設定変更が容易

### 5. 並列化の可能性
```python
# 将来的に並列化が可能
from concurrent.futures import ThreadPoolExecutor

def run_simulation(self, num_walkers: int):
    walkers = self.walker_service.generate_walkers(num_walkers)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(self._process_walker, walker, i)
            for i, walker in enumerate(walkers)
        ]
        results = [f.result() for f in futures]

    # 結果をマージ
    ...
```

## 移行計画

### Phase 1: サービスクラス作成
1. services/ ディレクトリ作成
2. 各サービスクラスを実装
3. 既存のコードから機能を移植

### Phase 2: オーケストレーター作成
1. SimulationService を実装
2. 既存の generate_simulation() と同等の機能を実現

### Phase 3: main.py リファクタリング
1. 依存性注入パターンを実装
2. サービスのインスタンス化を追加

### Phase 4: 検証と移行
1. 既存の出力と新実装の出力が一致することを確認
2. 古い generate_simulation.py を削除

### Phase 5: テスト追加
1. 各サービスのユニットテスト作成
2. 統合テストの追加
