# File: app/core/model_lifecycle/types.py

from enum import Enum

class ModelType(str, Enum):
    WHISPER = "whisper"
    NEMO_VAD = "nemo_vad"
    NEMO_DIARIZATION = "nemo_diarization"
    QWEN_VL = "qwen_vl"