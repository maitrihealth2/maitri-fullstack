"""
Voice API — Phase 3 Multi-language
Full pipeline: audio → STT → crisis → emotion → RAG → LLM → TTS → audio
"""

import base64
import traceback
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database.models import get_db, Session as DBSession, Message, MessageEmotion, RiskLog, User
from providers.sarvam.voice_client import synthesize_speech, get_language_prompt, get_supported_languages
from modules.voice.stt_batcher import batch_transcribe_audio
from providers.sarvam.sarvam_client import chat_with_maitri
from rag.brain.emotion_detector import detect_emotion, detect_emotion_heuristic
from rag.brain.analyst import should_skip_assessor, assess_turn
from modules.voice.vocal_engine import optimize_pitch
from security.crisis_handler import check_for_crisis
from rag.brain.state_tracker import tracker
from security.authentication.api import get_current_user
from modules.dashboard.api import broadcast_event

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/languages")
def list_languages():
    return get_supported_languages()


class SpeakRequest(BaseModel):
    text: str
    language: str = "en-IN"


@router.post("/speak")
async def speak(
    req: SpeakRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        audio_bytes = await synthesize_speech(req.text, req.language)
        # Apply Vocal Prosody Optimization
        audio_bytes = await asyncio.to_thread(optimize_pitch, audio_bytes, "Neutral")
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        print(f"[VOICE] Speak failed: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="en-IN"),
    current_user: User = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    print(f"[TRANSCRIBE] size={len(audio_bytes)} lang={language}")
    if len(audio_bytes) < 500:
        return {"transcript": "", "language": language}
    try:
        transcript = await batch_transcribe_audio(audio_bytes, language)
        return {"transcript": transcript, "language": language}
    except Exception as e:
        print(f"[VOICE] Transcribe failed: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_voice_turn(
    transcript: str,
    session_id: str,
    language: str,
    current_user: User,
    db: Session,
):
    """
    Process a single voice turn: Crisis check -> Emotion -> RAG -> LLM -> TTS.
    Returns the full response dictionary.
    """
    # ── Validate session ──────────────────────────────────────────────────────
    session = db.query(DBSession).filter(
        DBSession.session_token == session_id,
        DBSession.user_id == current_user.id,
    ).first()
    if not session:
        print(f"[VOICE] ERROR: Session not found")
        raise HTTPException(status_code=404, detail="Session not found")
    print(f"[VOICE] Session DB id={session.id} OK")

    # Filter known STT hallucinations when there's background noise
    known_hallucinations = [
        "thank you.", "thank you", "subscribe", "subscribe.", 
        "subscribe to the channel", "subtitles by amara.org", 
        "[silence]", "you", "thanks."
    ]
    cleaned_transcript = transcript.strip().lower()
    if not cleaned_transcript or cleaned_transcript in known_hallucinations or len(cleaned_transcript) < 2:
        print(f"[VOICE] Empty or hallucinated transcript: '{transcript}' — treating as silence")
        return {
            "transcript": "",
            "response": "",
            "audio_b64": "",
            "is_crisis": False,
            "helplines": [],
            "emotion": "Neutral",
            "emotion_emoji": "😐",
            "emotion_score": 0.0,
            "rag_used": False,
        }
        
    await broadcast_event("STT_DONE", f"Transcribed text", {"text": transcript})

    # ── Crisis check ──────────────────────────────────────────────────────────
    print(f"[VOICE] Crisis check...")
    crisis = check_for_crisis(transcript)
    if crisis.is_crisis:
        print(f"[VOICE] CRISIS detected: {crisis.trigger_phrase}")
        db.add(RiskLog(
            session_id=session.id, user_id=current_user.id,
            trigger_phrase=crisis.trigger_phrase or transcript[:200],
            system_response="AI intervened with extreme comfort.", helpline_shown=True,
        ))
        session.is_crisis_flagged = True
        db.commit()

    # ── Emotion + LLM ────────────────────────────────────────────────────────
    print(f"[VOICE] Computing emotion heuristically and calling LLM...")
    await broadcast_event("ROUTING", "STT Text -> AI Brain Cluster")
    
    # Bypass RAG completely for voice to save 1-2 seconds of latency
    rag_context = ""

    # Append voice brevity instructions to lang_prompt
    lang_prompt = get_language_prompt(language)
    lang_prompt += " Keep your response conversational and natural, as this is a real-time voice call. Provide clear reasoning if needed."

    # Fetch last 30 messages for this specific session
    past = db.query(Message).filter(
        Message.session_id == session.id
    ).order_by(Message.created_at.desc()).limit(30).all()
    past.reverse()
    
    history = [{"role": m.role, "content": m.content} for m in past]
    history.append({"role": "user", "content": transcript})
    
    # ── Sequential Processing: Emotion -> Analyst -> LLM ─────────────────────
    # 1. Get True Emotion from local HuggingFace pipeline
    try:
        emotion = await asyncio.wait_for(detect_emotion(transcript), timeout=2.0)
        print(f"[VOICE] DL Emotion: {emotion.label} ({emotion.score:.2f})")
    except Exception as te:
        print(f"[VOICE] DL Emotion timeout/error, falling back to heuristic")
        emotion = detect_emotion_heuristic(transcript)

    await broadcast_event("EMOTION_DETECTED", f"Detected: {emotion.label}", {"emotion": emotion.label, "score": emotion.score})

    # Update State Tracker
    tracker.update_emotion(session.id, emotion.label)
    if crisis.is_crisis:
        tracker.set_crisis_risk(session.id, "High")
    state_summary = tracker.get_summary(session.id)

    # 2. MAITRI AGENT LOOP v2: Assessor Phase Check
    case_file = tracker.get_case_file(session.id)
    if should_skip_assessor(transcript, case_file):
        await broadcast_event("LLM_START", "Assessor Skipped (Trivial Input)")
        print(f"[VOICE] Assessor skipped via fast-path filter")
        case_file["runtime_state"]["decision"] = "RESPOND"
    else:
        await broadcast_event("LLM_START", "Assessor Evaluating...")
        case_file = await assess_turn(
            messages=history,
            case_file=case_file,
            user_message=transcript,
            emotion_label=emotion.label,
            rag_context=rag_context,
            pattern_block="",
            persona_summary=state_summary,
        )
        tracker.update_case_file(session.id, case_file)
        print(f"[VOICE] Assessor Decision: {case_file.get('runtime_state', {}).get('decision')}")

    # 3. Generate response with Maitri (passing the case file)
    await broadcast_event("LLM_START", "Maitri Generation...")
    
    try:
        ai_response = await asyncio.to_thread(
            chat_with_maitri,
            messages=history,
            language=language,
            rag_context=rag_context,
            case_file=case_file,
            language_prompt=lang_prompt,
            max_tokens=1500,
            reasoning_effort=None,
            is_crisis=crisis.is_crisis,
        )
        await broadcast_event("LLM_DONE", "Response generated", {"response": ai_response})
        print(f"[VOICE] LLM response: '{ai_response[:80]}...'")
    except Exception as e:
        print(f"[VOICE] LLM call failed: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail={"message": f"LLM pipeline failed: {str(e)}"})

    # ── Save to DB ────────────────────────────────────────────────────────────
    try:
        user_msg = Message(session_id=session.id, role="user", content=transcript, language=language)
        db.add(user_msg)
        db.flush()

        if emotion and emotion.label:
            db.add(MessageEmotion(message_id=user_msg.id, emotion_label=emotion.label, score=emotion.score))

        ai_msg = Message(session_id=session.id, role="assistant", content=ai_response, language=language)
        db.add(ai_msg)
        db.commit()
    except Exception as e:
        print(f"[VOICE] DB save failed (continuing): {type(e).__name__} - {e}")

    # ── TTS ───────────────────────────────────────────────────────────────────
    print(f"[VOICE] Calling TTS...")
    audio_b64 = ""
    try:
        # Reuse user's emotion to determine voice tone instead of calling HF API again
        await broadcast_event("ROUTING", "LLM -> TTS API")
        await broadcast_event("TTS_START", "Synthesizing voice...")
        response_audio = await synthesize_speech(
            ai_response, 
            language, 
            emotion=emotion.label
        )
        # 6. Prosody & Pitch Optimization
        await broadcast_event("TTS_OPTIMIZE", "Optimizing vocal pitch and prosody...")
        response_audio = await asyncio.to_thread(optimize_pitch, response_audio, emotion.label)
        
        audio_b64 = base64.b64encode(response_audio).decode()
        await broadcast_event("TTS_DONE", "Audio ready")
        await broadcast_event("ROUTING", "FastAPI -> Client WebSocket Playback")
        print(f"[VOICE] TTS OK, audio size={len(response_audio)} bytes")
    except Exception as e:
        print(f"[VOICE] TTS failed: {type(e).__name__} - {e}")

    return {
        "transcript": transcript,
        "response": ai_response,
        "audio_b64": audio_b64,
        "is_crisis": crisis.is_crisis,
        "helplines": crisis.helplines if crisis.is_crisis else [],
        "emotion": emotion.label,
        "emotion_emoji": emotion.emoji,
        "emotion_score": emotion.score,
        "rag_used": bool(rag_context),
    }


@router.post("/conversation")
async def voice_conversation(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    language: str = Form(default="en-IN"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print(f"\n{'='*60}")
    print(f"[VOICE] POST Request session={session_id} lang={language}")

    # ── Read audio ────────────────────────────────────────────────────────────
    audio_bytes = await audio.read()
    if len(audio_bytes) < 500:
        print("[VOICE] Audio too short or empty, treating as silence")
        return await handle_voice_turn("[Silence]", session_id, language, current_user, db)

    # ── STT ───────────────────────────────────────────────────────────────────
    try:
        await broadcast_event("ROUTING", "FastAPI -> Sarvam STT API")
        await broadcast_event("STT_START", "Transcribing (Batched)...")
        transcript = await batch_transcribe_audio(audio_bytes, language)
    except Exception as e:
        err_str = str(e)
        if "duration exceeds the maximum limit" in err_str:
            print("[VOICE] 30s limit hit. Gracefully prompting user.")
            msg = "I'm sorry, that was a bit too long for me to process at once. Could you repeat that in shorter pieces?"
            try:
                err_audio = await synthesize_speech(msg, language)
                if err_audio:
                    err_audio = await asyncio.to_thread(optimize_pitch, err_audio, "Neutral")
                    err_b64 = base64.b64encode(err_audio).decode()
            except Exception:
                err_b64 = ""
            return {
                "transcript": "[Audio too long]",
                "response": msg,
                "audio_b64": err_b64,
                "is_crisis": False,
                "helplines": [],
                "emotion": "Neutral",
                "emotion_emoji": "😐",
                "emotion_score": 0.0,
                "rag_used": False,
            }
        print(f"[VOICE] STT failed: {type(e).__name__} - {err_str}")
        raise HTTPException(status_code=500, detail={"message": f"STT failed: {err_str}"})

    return await handle_voice_turn(transcript, session_id, language, current_user, db)
