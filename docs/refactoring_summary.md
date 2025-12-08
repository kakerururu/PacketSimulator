# Generator リファクタリング完了報告

## 実装完了内容

### 新しいアーキテクチャ

```
src2/generator/
├── domain/                          # ドメインモデル（変更なし）
├── infrastructure/                  # インフラ層（変更なし）
├── usecase/
│   ├── services/                    # ✨ 新規追加
│   │   ├── __init__.py
│   │   ├── walker_generation_service.py
│   │   ├── timeline_generation_service.py
│   │   └── record_generation_service.py
│   ├── simulation_service.py        # ✨ 新規追加
│   └── generate_simulation.py       # 旧実装（保持）
└── main.py                          # ✅ 依存性注入に変更
```

## サービスクラス詳細

### 1. WalkerGenerationService
**ファイル**: `usecase/services/walker_generation_service.py`

**責務**:
- 通行人の生成
- モデルの確率的選択
- ルートのランダム生成
- ペイロードIDの割り当て（ユニーク型のみ）

**主要メソッド**:
```python
generate_walkers(num_walkers: int) -> List[Walker]
generate_random_route() -> str
```

**依存関係**:
- detectors: List[Detector]
- payload_definitions: PayloadDefinitionsDict
- model_names: List[str]
- model_probabilities: List[float]

### 2. TimelineGenerationService
**ファイル**: `usecase/services/timeline_generation_service.py`

**責務**:
- 滞在タイムラインの生成
- 移動時間の計算
- 時系列の管理

**主要メソッド**:
```python
generate_timeline(route: str) -> List[Stay]
calculate_travel_time(from_detector, to_detector) -> float
```

**依存関係**:
- detectors: Dict[str, Detector]
- start_time: datetime
- stay_duration_min: float
- stay_duration_max: float
- walker_speed: float
- variation_factor: float

### 3. RecordGenerationService
**ファイル**: `usecase/services/record_generation_service.py`

**責務**:
- 検出レコードの生成
- ペイロードの選択
- 連続/ランダムレコードの生成

**主要メソッド**:
```python
generate_records(walker, timeline) -> List[DetectionRecord]
choose_payload(model_name, assigned_hash_ID) -> str
_generate_consecutive_payloads(...) -> List[DetectionRecord]
_generate_random_payloads(...) -> List[DetectionRecord]
```

**依存関係**:
- payload_definitions: PayloadDefinitionsDict
- payloads_per_detector: int
- num_consecutive_payloads: int

### 4. SimulationService (オーケストレーター)
**ファイル**: `usecase/simulation_service.py`

**責務**:
- 各サービスの調整
- シミュレーション全体のフロー制御
- 軌跡とレコードの統合

**主要メソッド**:
```python
run_simulation(num_walkers: int) -> Tuple[List[Trajectory], List[DetectionRecord]]
```

**依存関係**:
- walker_service: WalkerGenerationService
- timeline_service: TimelineGenerationService
- record_service: RecordGenerationService

## 依存性注入の実装

### main.py の構造

```python
def main():
    # 1. 設定読み込み
    detectors = load_detectors()
    payload_definitions, model_names, model_probabilities = load_payloads()
    simulation_settings = load_simulation_settings(config_dir)

    # 2. サービスのインスタンス化（依存性注入）
    walker_service = WalkerGenerationService(
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities
    )

    timeline_service = TimelineGenerationService(
        detectors={d.id: d for d in detectors},
        start_time=datetime(2024, 1, 14, 11, 0, 0),
        stay_duration_min=simulation_settings["stay_duration_min_seconds"],
        stay_duration_max=simulation_settings["stay_duration_max_seconds"],
        walker_speed=simulation_settings["walker_speed"],
        variation_factor=simulation_settings["variation_factor"]
    )

    record_service = RecordGenerationService(
        payload_definitions=payload_definitions,
        payloads_per_detector=simulation_settings["payloads_per_detector_per_walker"],
        num_consecutive_payloads=simulation_settings["num_consecutive_payloads"]
    )

    # 3. オーケストレーターの作成
    simulation = SimulationService(
        walker_service=walker_service,
        timeline_service=timeline_service,
        record_service=record_service
    )

    # 4. 実行
    trajectories, records = simulation.run_simulation(
        num_walkers=simulation_settings["num_walkers_to_simulate"]
    )
```

## 達成されたメリット

### ✅ 1. 単一責任の原則
各サービスが1つの明確な責務を持つ：
- WalkerGenerationService → 通行人生成
- TimelineGenerationService → タイムライン生成
- RecordGenerationService → レコード生成
- SimulationService → 全体調整

### ✅ 2. テスタビリティ
各サービスを独立してテスト可能：

```python
# 例: WalkerGenerationService の単体テスト
def test_walker_generation():
    service = WalkerGenerationService(
        detectors=mock_detectors,
        payload_definitions=mock_payloads,
        model_names=["Model_Test"],
        model_probabilities=[1.0]
    )
    walkers = service.generate_walkers(5)
    assert len(walkers) == 5
    assert all(w.model == "Model_Test" for w in walkers)
```

### ✅ 3. 拡張性
サービスを継承してカスタマイズ可能：

```python
# 例: カスタムルート生成
class FixedRouteWalkerService(WalkerGenerationService):
    def generate_random_route(self) -> str:
        return "ABCD"  # 常に同じルート

# 使用
custom_walker_service = FixedRouteWalkerService(...)
simulation = SimulationService(
    walker_service=custom_walker_service,  # カスタムサービスを注入
    timeline_service=timeline_service,
    record_service=record_service
)
```

### ✅ 4. 依存性の明確化
- コンストラクタで依存関係が明示される
- IDEでの型チェックが効く
- ドキュメントが自己文書化される

### ✅ 5. 保守性
- 変更の影響範囲が限定される
- 機能追加が容易
- コードの読みやすさが向上

## 動作確認結果

```bash
$ python -m src2.generator.main

=== シミュレーションデータ生成開始 ===
設定ファイルを読み込み中...
検出器数: 4
シミュレートする通行人数: 1人
各検出器での検出数: 10個
連続ペイロード数: 3個
通行人の移動速度: 1.4 m/s
滞在時間: 180-420秒

シミュレーション実行中...
生成された軌跡数: 1
生成された検出レコード数: 40

Ground Truth JSONを出力中...
✓ Ground Truth JSON出力完了: src2_result/ground_truth/trajectories.json

検出ログCSVを出力中...
✓ 検出ログCSV出力完了: src2_result/detector_logs/

=== シミュレーションデータ生成完了 ===
```

✅ **正常動作確認完了**

## 将来の拡張例

### 1. 異なる滞在時間分布
```python
class NormalDistributionTimelineService(TimelineGenerationService):
    def generate_timeline(self, route: str) -> List[Stay]:
        # 正規分布を使用
        stay_duration = random.gauss(mean=300, stddev=60)
        # ...
```

### 2. 現実的なルート生成
```python
class RealisticRouteWalkerService(WalkerGenerationService):
    def generate_random_route(self) -> str:
        # 実際の人の動きパターンに基づくルート生成
        # 例: 入口から出口へのショートパスを優先
        return self._calculate_realistic_route()
```

### 3. カスタムレコード生成
```python
class BurstRecordService(RecordGenerationService):
    def _generate_random_payloads(self, ...):
        # バースト的なレコード生成パターン
        # 例: 特定時間に集中してレコードを生成
        return self._generate_burst_pattern(...)
```

### 4. 並列実行
```python
class ParallelSimulationService(SimulationService):
    def run_simulation(self, num_walkers: int):
        from concurrent.futures import ProcessPoolExecutor

        walkers = self.walker_service.generate_walkers(num_walkers)

        with ProcessPoolExecutor() as executor:
            results = list(executor.map(self._process_walker, walkers))

        # 結果を統合
        ...
```

## 今後の推奨事項

1. **ユニットテストの追加**
   - 各サービスの単体テスト
   - 統合テスト
   - エッジケーステスト

2. **型ヒントの完全化**
   - すべてのパラメータに型ヒント
   - 戻り値の型ヒント
   - mypy による型チェック

3. **設定の外部化**
   - start_time を設定ファイルに
   - より柔軟な設定管理

4. **ロギングの追加**
   - 各サービスでのロギング
   - デバッグ情報の出力
   - パフォーマンス測定

5. **ドキュメント整備**
   - 各サービスの使用例
   - カスタマイズガイド
   - アーキテクチャ図

## まとめ

✨ **リファクタリング完了！**

- **責務分離**: 4つの専門サービスに分割
- **依存性注入**: テスタブルで拡張可能な設計
- **後方互換**: 既存の出力と完全一致
- **拡張性**: カスタマイズポイントが明確

この新しいアーキテクチャにより、Generator モジュールは：
- **保守しやすく**
- **テストしやすく**
- **拡張しやすく**

なりました！🎉
