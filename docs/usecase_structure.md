# Generator ユースケース層の構造

## ディレクトリ構成

```
src2/generator/usecase/
├── walker_generation.py        # 通行人生成
├── timeline_generation.py      # タイムライン生成
├── record_generation.py        # レコード生成
├── simulation.py               # シミュレーション実行
└── generate_simulation.py      # 旧実装（保持）
```

## 責務ごとの分割

### 1. walker_generation.py
**責務**: 通行人の生成

**関数**:
- `generate_random_route(detectors)` - ランダムなルート生成
- `generate_walkers(...)` - 通行人リストを生成

**処理内容**:
1. 指定された数の通行人を生成
2. 各通行人にモデルを確率的に割り当て
3. ユニーク型モデルには固定ペイロードIDを割り当て
4. ランダムなルートを生成

### 2. timeline_generation.py
**責務**: 滞在タイムラインの生成

**関数**:
- `calculate_travel_time(from, to, speed, variation)` - 移動時間計算
- `generate_timeline(route, ...)` - タイムライン生成

**処理内容**:
1. ルート上の各検出器での滞在情報を生成
2. 到着・出発時刻を計算
3. 滞在時間をランダムに決定 (180-420秒)
4. 次の検出器への移動時間を計算

### 3. record_generation.py
**責務**: 検出レコードの生成

**関数**:
- `choose_payload(model, assigned_id, definitions)` - ペイロード選択
- `generate_detection_records(walker, timeline, ...)` - レコード生成

**処理内容**:
1. 各滞在期間中にレコードを生成
2. 連続ペイロード (シーケンス番号連続) の生成
3. ランダムペイロードの生成
4. タイムスタンプでソート

### 4. simulation.py
**責務**: シミュレーション全体の実行

**関数**:
- `run_simulation(...)` - シミュレーション実行

**処理内容**:
1. 通行人を生成
2. 各通行人のタイムラインを生成
3. 各通行人のレコードを生成
4. 軌跡オブジェクトを作成
5. すべての結果を返す

## main.py での使用方法

```python
from .usecase import simulation

# 設定読み込み
detectors = load_detectors()
payload_definitions, model_names, model_probabilities = load_payloads()
settings = load_simulation_settings(config_dir)

# シミュレーション実行
trajectories, detection_records = simulation.run_simulation(
    detectors=detectors,
    payload_definitions=payload_definitions,
    model_names=model_names,
    model_probabilities=model_probabilities,
    num_walkers=settings["num_walkers_to_simulate"],
    start_time=datetime(2024, 1, 14, 11, 0, 0),
    stay_duration_min=settings["stay_duration_min_seconds"],
    stay_duration_max=settings["stay_duration_max_seconds"],
    walker_speed=settings["walker_speed"],
    variation_factor=settings["variation_factor"],
    payloads_per_detector=settings["payloads_per_detector_per_walker"],
    num_consecutive_payloads=settings["num_consecutive_payloads"],
)
```

## データフロー

```
main.py
  ↓ (設定読み込み)
  ↓
simulation.run_simulation()
  │
  ├─→ walker_generation.generate_walkers()
  │     └─→ walker_generation.generate_random_route()
  │
  └─→ 各通行人に対して:
        │
        ├─→ timeline_generation.generate_timeline()
        │     └─→ timeline_generation.calculate_travel_time()
        │
        ├─→ Trajectory オブジェクト作成
        │
        └─→ record_generation.generate_detection_records()
              └─→ record_generation.choose_payload()
```

## 各ユースケースの独立性

各ユースケースは独立した関数として実装されているため：

### ✅ テストしやすい
```python
# 個別の関数をテスト可能
def test_generate_random_route():
    detectors = [Detector("A", 0, 0), Detector("B", 100, 0)]
    route = walker_generation.generate_random_route(detectors)
    assert len(route) == 2
    assert set(route) == {"A", "B"}
```

### ✅ 拡張しやすい
```python
# カスタムロジックに置き換え可能
def my_custom_route_generator(detectors):
    # カスタムロジック
    return "ABC"

# simulation.py で使用する関数を変更するだけ
```

### ✅ 理解しやすい
- 各ファイルが1つの責務
- 関数名が処理内容を表現
- シンプルな入出力

## メリット

1. **シンプル**: クラスや複雑な概念なし、関数ベース
2. **明確**: 各ファイルの責務が明確
3. **保守**: 変更の影響範囲が限定される
4. **拡張**: 必要な関数だけ置き換え可能
5. **テスト**: 各関数を独立してテスト可能

## 実行確認

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

✓ 動作確認完了
```
