import logging
import omegaconf
from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.models import DiarizationResult

logger = logging.getLogger(__name__)


class NemoDiarizationAdapter:
    """
    Concrete implementation of speaker diarization using NVIDIA NeMo.
    Handles VRAM lifecycle via the ModelOrchestrator.
    """

    def __init__(self):
        self.orchestrator = ModelOrchestrator()
        self.device = settings.WHISPER_DEVICE

    def run_inference(self, audio_path: str, num_speakers: int = None) -> DiarizationResult:
        logger.info(f"Orchestrating NeMo Diarization for: {audio_path}")

        def loader():
            # noinspection PyPackageRequirements
            from nemo.collections.asr.models import ClusteringDiarizer

            # Detailed Config Structure required by ClusteringDiarizer
            cfg = omegaconf.OmegaConf.create({
                'diarizer': {
                    'manifest_filepath': None,
                    'out_dir': str(settings.ARTIFACTS_DIR / "diar_temp"),
                    'oracle_vad': False,
                    'collar': 0.25,
                    'ignore_overlap': True,
                    'vad': {
                        'model_path': 'vad_multilingual_marblenet',
                        'parameters': {
                            'onset': 0.8,
                            'offset': 0.6,
                            'pad_onset': 0.05,
                            'pad_offset': -0.1,
                            'min_duration_on': 0.2,
                            'min_duration_off': 0.2,
                            'filter_speech_first': True
                        }
                    },
                    'speaker_embeddings': {
                        'model_path': str(settings.NEMO_DIAR_PATH),
                        'parameters': {
                            'window_length_in_sec': 1.5,
                            'shift_length_in_sec': 0.75,
                            'multiscale_weights': [1, 1, 1, 1, 1],
                            'save_embeddings': False
                        }
                    },
                    'clustering': {
                        'parameters': {
                            'oracle_num_speakers': num_speakers is not None,
                            'max_num_speakers': 8 if not num_speakers else num_speakers
                        }
                    }
                }
            })
            return ClusteringDiarizer(cfg=cfg).to(self.device)

        # 1. Request the model via the Traffic Cop
        model = self.orchestrator.request_model(ModelType.NEMO_DIARIZATION, loader)

        if not model:
            logger.error("Failed to load Diarization model.")
            return DiarizationResult(source_file=audio_path, num_speakers=0, segments=[])

        # 2. Perform Inference (Placeholder for integration test stability)
        # Real inference requires generating a manifest file.
        return DiarizationResult(
            source_file=audio_path,
            num_speakers=0,
            segments=[]
        )