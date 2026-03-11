import logging
import torch

logger = logging.getLogger(__name__)

def check_hardware_acceleration():
    """서버 구동 시 GPU 및 CUDA 가용성을 체크합니다."""
    logger.info("Checking Hardware Acceleration for AI-Pass Core...")
    
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0)
        cuda_version = torch.version.cuda
        cudnn_enabled = torch.backends.cudnn.enabled
        
        logger.info(f"[SUCCESS] CUDA is available! Found {device_count} device(s).")
        # [수정 완료] CUDA 및 cuDNN 버전 상세 로깅 추가
        logger.info(f"[SUCCESS] Primary GPU: {device_name} (CUDA: {cuda_version}, cuDNN: {cudnn_enabled})")
    else:
        logger.warning("[WARNING] CUDA is not available. Falling back to CPU. Performance may be severely degraded.")