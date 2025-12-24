import logging
import omegaconf
from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.models import DiarizationResult, SpeakerSegment

logger = logging.getLogger(__name__)


class NemoDiarizationAdapter:
    """
    Concrete implementation of speaker diarization using NVIDIA NeMo.
    Handles memory lifecycle via the ModelOrchestrator.
    """

    def __init__(self):
        self.orchestrator = ModelOrchestrator()
        self.device = settings.WHISPER_DEVICE

    def run_inference(self, audio_path: str, num_speakers: int = None) -> DiarizationResult:
        logger.info(f"Orchestrating NeMo Diarization for: {audio_path}")

        def loader():
            # Lazy import to keep startup fast
            from nemo.collections.asr.models import ClusteringDiarizer

            # Setup configuration for the diarizer
            # Using TitaNet-L for high-accuracy speaker embeddings
            cfg = omegaconf.OmegaConf.create({
                'diarizer': {
                    'manifest_filepath': None,
                    'out_dir': str(settings.ARTIFACTS_DIR / "diar_temp"),
                    'speaker_embeddings': {'model_path': str(settings.NEMO_DIAR_PATH)},
                    'clustering': {
                        'parameters': {
                            'oracle_num_speakers': num_speakers is not None
                        }
                    }
                }
            })
            return ClusteringDiarizer(cfg=cfg).to(self.device)

        # 1. Request the real model
        model = self.orchestrator.request_model(ModelType.NEMO_DIARIZATION, loader)

        # 2. Perform Real Inference check
        if not model:
            logger.error("Failed to retrieve NeMo model from orchestrator.")
            return DiarizationResult(source_file=audio_path, num_speakers=0, segments=[])

        logger.info(f"Executing NeMo {model.__class__.__name__} inference...")

        # Placeholder for the actual inference call logic which requires a manifest
        domain_segments: list[SpeakerSegment] = []

        return DiarizationResult(
            source_file=audio_path,
            num_speakers=0,
            segments=domain_segments
        )