# services/audio_transcription.py

import os
import tempfile
from typing import Optional

from src.utils.logger import get_logger
from src.utils.rotator import APIKeyRotator, robust_post_json

logger = get_logger("AUDIO_TRANSCRIPTION", __name__)

# NVIDIA Riva configuration
RIVA_SERVER = "api.nvcf.nvidia.com"
RIVA_FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"

async def transcribe_audio_file(
    audio_file_path: str,
    rotator: APIKeyRotator,
    language_code: str = "en"
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
            
        # Prepare the request - using NVIDIA's API format
        url = f"https://{RIVA_SERVER}/v1/speech/transcribe"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/octet-stream"
        }
        
        # Read audio file
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            
        # Prepare metadata for NVIDIA API
        metadata = {
            "function-id": RIVA_FUNCTION_ID,
            "language-code": language_code
        }
        
        # Add metadata to headers
        for key, value in metadata.items():
            headers[f"x-{key}"] = value
            
        # Make the request
        logger.info(f"Transcribing audio file: {audio_file_path} (language: {language_code})")
        
        # Use httpx for binary data upload
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    content=audio_data
                )
                
                if response.status_code in (401, 403, 429) or (500 <= response.status_code < 600):
                    logger.warning(f"HTTP {response.status_code} from Riva API. Rotating key and retrying...")
                    rotator.rotate()
                    # Retry with new key
                    api_key = rotator.get_key()
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                        response = await client.post(url, headers=headers, content=audio_data)
                        
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                transcribed_text = result.get("transcript", "").strip()
                
                if transcribed_text:
                    logger.info(f"Successfully transcribed audio: {len(transcribed_text)} characters")
                    return transcribed_text
                else:
                    logger.warning("Transcription returned empty result")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
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
