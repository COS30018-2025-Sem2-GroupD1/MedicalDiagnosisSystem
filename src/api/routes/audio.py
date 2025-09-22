# api/routes/audio.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from src.core.state import MedicalState, get_state
from src.services.audio_transcription import (
    transcribe_audio_bytes,
    validate_audio_format,
    get_supported_formats
)
from src.utils.logger import get_logger

logger = get_logger("AUDIO_API", __name__)

router = APIRouter(prefix="/audio", tags=["audio"])

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language_code: str = Form(default="en"),
    state: MedicalState = Depends(get_state)
) -> JSONResponse:
    """
    Transcribe audio file to text using NVIDIA Riva API.
    
    Args:
        file: Audio file (WAV, OPUS, FLAC, or WebM format)
        language_code: Language code for transcription (default: 'en')
        state: Application state
        
    Returns:
        JSON response with transcribed text
    """
    try:
        # Validate file type
        if not file.content_type or not any(
            file.content_type.startswith(f"audio/{fmt}") 
            for fmt in ["wav", "opus", "flac", "webm"]
        ):
            # Also check file extension as fallback
            file_extension = file.filename.split('.')[-1].lower() if file.filename else ""
            if file_extension not in get_supported_formats():
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format. Supported formats: {', '.join(get_supported_formats())}"
                )
        
        # Read audio data
        audio_bytes = await file.read()
        
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
            
        # Validate audio format
        if not validate_audio_format(audio_bytes):
            raise HTTPException(
                status_code=400,
                detail="Invalid audio format. Please ensure the file is a valid WAV, OPUS, or FLAC file."
            )
        
        # Transcribe audio
        logger.info(f"Transcribing audio file: {file.filename} (language: {language_code})")
        transcribed_text = await transcribe_audio_bytes(
            audio_bytes, 
            state.nvidia_rotator,
            language_code
        )
        
        if transcribed_text is None:
            raise HTTPException(
                status_code=500,
                detail="Transcription failed. Please try again or check your audio file."
            )
            
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "transcribed_text": transcribed_text,
                "language_code": language_code,
                "file_name": file.filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during transcription"
        )

@router.get("/supported-formats")
async def get_audio_formats() -> JSONResponse:
    """
    Get list of supported audio formats for transcription.
    
    Returns:
        JSON response with supported formats
    """
    return JSONResponse(
        status_code=200,
        content={
            "supported_formats": get_supported_formats(),
            "description": "Supported audio formats for transcription"
        }
    )

@router.get("/health")
async def audio_health_check(state: MedicalState = Depends(get_state)) -> JSONResponse:
    """
    Check if audio transcription service is available.
    
    Returns:
        JSON response with service status
    """
    try:
        # Check if NVIDIA API keys are available
        nvidia_keys_available = len([k for k in state.nvidia_rotator.keys if k]) > 0
        
        return JSONResponse(
            status_code=200,
            content={
                "service": "audio_transcription",
                "status": "available" if nvidia_keys_available else "unavailable",
                "nvidia_keys_available": nvidia_keys_available,
                "supported_formats": get_supported_formats()
            }
        )
    except Exception as e:
        logger.error(f"Audio health check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "service": "audio_transcription",
                "status": "error",
                "error": str(e)
            }
        )
