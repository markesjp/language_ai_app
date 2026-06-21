from fastapi import APIRouter, File, UploadFile

from app.services.speech.interfaces import MockSttProvider, MockTtsProvider

router = APIRouter()


@router.post("/stt")
async def stt(audio: UploadFile = File(...)) -> dict:
    provider = MockSttProvider()
    text, usage = await provider.transcribe(await audio.read())
    return {"text": text, "usage": usage.__dict__}


@router.post("/tts")
async def tts(payload: dict) -> dict:
    provider = MockTtsProvider()
    audio, usage = await provider.synthesize(
        str(payload.get("text", "")),
        payload.get("voice"),
        payload.get("model"),
        payload.get("speed"),
    )
    return {
        "audio_base64": "",
        "bytes": len(audio),
        "preset_id": payload.get("preset_id"),
        "voice": payload.get("voice"),
        "speed": payload.get("speed"),
        "usage": usage.__dict__,
    }
