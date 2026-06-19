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
    audio, usage = await provider.synthesize(str(payload.get("text", "")), payload.get("voice"))
    return {"audio_base64": "", "bytes": len(audio), "usage": usage.__dict__}
