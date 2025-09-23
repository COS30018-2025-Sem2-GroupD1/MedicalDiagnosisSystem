# services/audio_transcription.py

import os
import tempfile
from typing import Optional

from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator

logger = get_logger("AUDIO_TRANSCRIPTION", __name__)

# NVIDIA Riva configuration
RIVA_SERVER = "grpc.nvcf.nvidia.com:443"
RIVA_FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"

async def transcribe_audio_file(
    audio_file_path: str,
    language_code: str,
    rotator: APIKeyRotator
) -> Optional[str]:
    """
    Transcribe audio file using NVIDIA Riva API.
    
    Args:
        audio_file_path: Path to the audio file (WAV, OPUS, or FLAC format)
        language_code: Language code for transcription (e.g., 'en', 'fr', 'multi')
        rotator: API key rotator for authentication
        
    Returns:
        Transcribed text or None if transcription fails
    """
    try:
        # Check if file exists
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
            
        # Get API key
        api_key = rotator.get_key()
        if not api_key:
            logger.error("No NVIDIA API key available for transcription")
            return None
            
        # Read audio file
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        # gRPC path using Riva Python client
        try:
            from riva.client import ASRService, Auth
            from riva.client.argparse_utils import add_asr_config
            from riva.client.proto import riva_asr_pb2
        except Exception:
            logger.error("nvidia-riva-client is not installed or unavailable")
            return None

        # Detect encoding from header
        encoding = riva_asr_pb2.AudioEncoding.ENCODING_UNSPECIFIED
        # WAV (RIFF...WAVE)
        if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            encoding = riva_asr_pb2.AudioEncoding.LINEAR_PCM
        # Ogg/Opus
        elif audio_data[:4] == b'OggS':
            encoding = riva_asr_pb2.AudioEncoding.OGG_OPUS
        # FLAC
        elif audio_data[:4] == b'fLaC':
            encoding = riva_asr_pb2.AudioEncoding.FLAC
        # WebM header (EBML) – often carries Opus; try OGG_OPUS as closest
        elif audio_data[:4] == b'\x1a\x45\xdf\xa3':
            encoding = riva_asr_pb2.AudioEncoding.OGG_OPUS

        # Build Auth with metadata for NVCF function + bearer
        metadata = [
            ("function-id", RIVA_FUNCTION_ID),
            ("authorization", f"Bearer {api_key}")
        ]

        try:
            auth = Auth(uri=RIVA_SERVER, use_ssl=True, metadata=metadata)
            asr = ASRService(auth)

            # Build recognition config
            config = riva_asr_pb2.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code=language_code,
                max_alternatives=1,
                enable_automatic_punctuation=True
            )

            logger.info(f"Transcribing audio file: {audio_file_path} (language: {language_code})")
            resp = asr.offline_recognize(audio_data, config)

            # Assemble transcript
            pieces = []
            for res in resp.results:
                if res.alternatives:
                    pieces.append(res.alternatives[0].transcript)
            text = " ".join(pieces).strip()
            if text:
                logger.info(f"Successfully transcribed audio: {len(text)} characters")
                return text
            logger.warning("Transcription returned empty result")
            return None
        except Exception as e:
            # On auth errors, rotate key once and retry quickly
            logger.warning(f"Riva gRPC error: {e}. Rotating key and retrying once")
            try:
                rotator.rotate()
                api_key2 = rotator.get_key()
                if not api_key2:
                    return None
                metadata2 = [
                    ("function-id", RIVA_FUNCTION_ID),
                    ("authorization", f"Bearer {api_key2}")
                ]
                auth2 = Auth(uri=RIVA_SERVER, use_ssl=True, metadata=metadata2)
                asr2 = ASRService(auth2)
                config2 = riva_asr_pb2.RecognitionConfig(
                    encoding=encoding,
                    sample_rate_hertz=16000,
                    language_code=language_code,
                    max_alternatives=1,
                    enable_automatic_punctuation=True
                )
                resp2 = asr2.offline_recognize(audio_data, config2)
                pieces2 = []
                for res in resp2.results:
                    if res.alternatives:
                        pieces2.append(res.alternatives[0].transcript)
                text2 = " ".join(pieces2).strip()
                return text2 or None
            except Exception as e2:
                logger.error(f"Audio transcription failed after retry: {e2}")
                return None
                
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return None

async def transcribe_audio_bytes(
    audio_bytes: bytes,
    language_code: str,
    rotator: APIKeyRotator
) -> Optional[str]:
    """
    Transcribe audio bytes using NVIDIA Riva API.
    
    Args:
        audio_bytes: Audio data as bytes
        language_code: Language code for transcription (e.g., 'en', 'fr', 'multi')
        rotator: API key rotator for authentication
        
    Returns:
        Transcribed text or None if transcription fails
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
            
        try:
            # Transcribe the temporary file
            result = await transcribe_audio_file(temp_file_path, language_code, rotator)
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
                
    except Exception as e:
        logger.error(f"Audio bytes transcription failed: {e}")
        return None

def validate_audio_format(audio_bytes: bytes) -> bool:
    """
    Validate if the audio bytes are in a supported format.
    
    Args:
        audio_bytes: Audio data as bytes
        
    Returns:
        True if format is supported, False otherwise
    """
    # Check for common audio file signatures
    if len(audio_bytes) < 12:
        return False
        
    # WAV format check (RIFF header)
    if audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
        return True
        
    # OPUS format check (OggS header)
    if audio_bytes[:4] == b'OggS':
        return True
        
    # FLAC format check (fLaC header)
    if audio_bytes[:4] == b'fLaC':
        return True
        
    # WebM format check (EBML header)
    if audio_bytes[:4] == b'\x1a\x45\xdf\xa3':
        return True
        
    return False

def get_supported_formats() -> list[str]:
    """
    Get list of supported audio formats.
    
    Returns:
        List of supported format extensions
    """
    return ['.wav', '.opus', '.flac', '.webm']
