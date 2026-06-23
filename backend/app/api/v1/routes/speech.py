import base64

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.audit.ledger import record_speech_usage
from app.services.speech.providers import speech_provider_router

router = APIRouter()


@router.post("/stt")
async def stt(
    audio: UploadFile = File(...),
    trace_id: str | None = Form(default=None),
    user_id: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    provider = speech_provider_router.get_stt()
    audio_bytes = await audio.read()
    text, usage = await provider.transcribe(audio_bytes, filename=audio.filename, content_type=audio.content_type)
    if trace_id or user_id:
        await record_speech_usage(session, trace_id=trace_id or "speech-stt", user_id=user_id, feature="speech.stt", usage=usage)
        await session.commit()
    return {"text": text, "usage": usage.__dict__}


@router.post("/tts")
async def tts(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    provider = speech_provider_router.get_tts()
    audio, usage = await provider.synthesize(
        str(payload.get("text", "")),
        payload.get("voice"),
        payload.get("model"),
        payload.get("speed"),
    )
    trace_id = payload.get("trace_id")
    user_id = payload.get("user_id")
    if trace_id or user_id:
        await record_speech_usage(session, trace_id=trace_id or "speech-tts", user_id=user_id, feature="speech.tts", usage=usage)
        await session.commit()
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii") if audio else "",
        "bytes": len(audio),
        "preset_id": payload.get("preset_id"),
        "voice": payload.get("voice"),
        "speed": payload.get("speed"),
        "usage": usage.__dict__,
    }
