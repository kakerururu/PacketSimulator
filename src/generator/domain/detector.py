import json
from utils.load import load_jsonc


class Detector:
    def __init__(self, id: str, x: float, y: float):
        self.id = id
        self.x = x
        self.y = y


def load_detectors(file_path: str) -> dict[str, Detector]:
    """jsoncファイルから検知器情報をロードし、IDをキー、バリューをDetectorオブジェクトとする辞書で返す"""
    data = load_jsonc(file_path)
    detectors: list[Detector] = []
    for detector in data["detectors"]:
        detectors.append(Detector(detector["id"], detector["x"], detector["y"]))
    return {detector.id: detector for detector in detectors}
