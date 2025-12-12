import logging
import json
import tempfile
import os
from pathlib import Path
from typing import List
from omegaconf import OmegaConf

try:
    from nemo.collections.asr.models import ClusteringDiarizer
except ImportError:
    ClusteringDiarizer = None

from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.interfaces import IDiarizer
from ..domain.models import DiarizationResult, DiarizationSegment

logger = logging.getLogger(__name__)

class NemoDiarizationAdapter(IDiarizer):
    def __init__(self):
        self.orchestrator = ModelOrchestrator()

    def identify_speakers(self, audio_path: Path, num_speakers: int = None) -> DiarizationResult:
        logger.info(f"Starting Real Diarization on {audio_path.name}")
        
        if not ClusteringDiarizer:
             raise ImportError("NeMo ASR is not installed")

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            manifest_path = work_dir / "input_manifest.json"
            
            # 1. Create Input Manifest
            meta = {
                'audio_filepath': str(audio_path.absolute()),
                'offset': 0,
                'duration': None,
                'label': 'infer',
                'text': '-',
                'num_speakers': num_speakers,
                'uniq_id': "id_1" 
            }
            with open(manifest_path, 'w') as f:
                f.write(json.dumps(meta) + '\n')

            # 2. Determine Device
            device_str = "cuda" if "cuda" in settings.WHISPER_DEVICE else "cpu"

            # 3. COMPLETE NeMo Configuration (No more whack-a-mole)
            # This follows the standard offline_diarization.yaml schema
            config_params = {
                "name": "ClusterDiarizer",
                "num_workers": 0,
                "sample_rate": 16000,
                "batch_size": 64,
                "device": device_str,
                "verbose": False,
                "diarizer": {
                    "manifest_filepath": str(manifest_path),
                    "out_dir": str(work_dir),
                    "oracle_vad": False,
                    "collar": 0.25,
                    "ignore_overlap": True,
                    "vad": {
                        "model_path": "vad_multilingual_marblenet",
                        "external_vad_manifest": None,
                        "parameters": {
                            "onset": 0.8,
                            "offset": 0.6,
                            "pad_onset": 0.05,
                            "pad_offset": -0.1,
                            "min_duration_on": 0.2,
                            "min_duration_off": 0.2,
                            "filter_speech_first": True,
                            "window_length_in_sec": 0.63,
                            "shift_length_in_sec": 0.08,
                            "smoothing": False,
                            "overlap": 0.875
                        }
                    },
                    "speaker_embeddings": {
                        "model_path": "titanet_large",
                        "parameters": {
                            "window_length_in_sec": 1.5,
                            "shift_length_in_sec": 0.75,
                            "multiscale_weights": [1, 1, 1, 1, 1],
                            "save_embeddings": False
                        }
                    },
                    "clustering": {
                        "parameters": {
                            "oracle_num_speakers": False,
                            "max_num_speakers": 8,
                            "enhanced_count_thresh": 80,
                            "max_rp_threshold": 0.25,
                            "sparse_search_volume": 30,
                            "maj_vote_spk_count": False
                        }
                    },
                    "msdd_model": {
                        "model_path": None, # Disable MSDD for speed
                        "parameters": {
                            "use_speaker_model_from_ckpt": True,
                            "infer_batch_size": 25,
                            "sigmoid_threshold": [0.7],
                            "seq_eval_mode": False,
                            "split_infer": True,
                            "diar_window_length": 50,
                            "overlap_infer": 0.5
                        }
                    }
                }
            }
            
            if num_speakers is not None:
                config_params["diarizer"]["clustering"]["parameters"]["max_num_speakers"] = num_speakers

            cfg = OmegaConf.create(config_params)

            def runner():
                diarizer = ClusteringDiarizer(cfg=cfg)
                return diarizer

            diarizer_instance = self.orchestrator.request_model(ModelType.NEMO_DIARIZATION, runner)
            
            # 4. Execute with Error Handling
            # NeMo raises ValueError if VAD finds no speech. We must catch this.
            try:
                diarizer_instance.diarize()
            except ValueError as e:
                if "contains silence" in str(e):
                    logger.warning("Diarization: No speech detected in audio file. Returning empty results.")
                    return DiarizationResult(source_id=str(audio_path), num_speakers=0, segments=[])
                raise e # Re-raise if it's a different error
            
            # 5. Parse Output
            rttm_folder = work_dir / "pred_rttms"
            rttm_files = list(rttm_folder.glob("*.rttm"))
            
            segments = []
            final_speaker_count = 0
            
            if rttm_files:
                segments = self._parse_rttm(rttm_files[0])
                unique_spks = set(s.speaker_label for s in segments)
                final_speaker_count = len(unique_spks)

            return DiarizationResult(
                source_id=str(audio_path),
                num_speakers=final_speaker_count,
                segments=segments
            )

    def _parse_rttm(self, rttm_path: Path) -> List[DiarizationSegment]:
        segments = []
        with open(rttm_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 8 and parts[0] == "SPEAKER":
                    start = float(parts[3])
                    duration = float(parts[4])
                    speaker = parts[7]
                    
                    segments.append(DiarizationSegment(
                        start=start,
                        end=start + duration,
                        speaker_label=speaker
                    ))
        return segments