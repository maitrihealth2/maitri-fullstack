import asyncio
import uuid
from typing import Dict, Any, List
from fastapi import HTTPException
from loguru import logger

from src.modules.consultation.repository import ConsultationRepository
from src.modules.consultation.schemas import StartSessionResponse, ChatRequest, ChatResponse
from src.database.models import User

# --- Legacy Integrations (To be migrated to src/engines later) ---
from rag.brain.emotion_detector import detect_emotion, detect_emotion_heuristic
from rag.brain.analyst import should_skip_assessor, assess_turn
from rag.brain.pattern_analyzer import analyze_patterns
from providers.sarvam.voice_client import get_language_prompt
from providers.sarvam.sarvam_client import chat_with_maitri
from security.crisis_handler import check_for_crisis
from modules.profile.service import get_persona_summary, update_persona
from rag.brain.state_tracker import tracker
from modules.dashboard.api import broadcast_event

try:
    from rag.knowledge.retriever import retrieve_context, is_knowledge_base_ready
except Exception as e:
    logger.warning(f"[RAG] Not available: {e}")
    def retrieve_context(query, n_results=3):
        return ""
    def is_knowledge_base_ready():
        return False

class ConsultationService:
    def __init__(self, repository: ConsultationRepository):
        self.repo = repository

    async def start_session(self, user: User) -> StartSessionResponse:
        token = str(uuid.uuid4())
        session = self.repo.create_session(user.id, token)
        
        session_count = self.repo.get_user_session_count(user.id)
        is_first = session_count == 1
        
        tracker.init_session(session.id, is_first_session=is_first)
        
        return StartSessionResponse(
            session_id=token,
            message="Session started.",
            is_first_session=is_first,
        )

    async def process_chat(self, req: ChatRequest, user: User) -> ChatResponse:
        session = self.repo.get_session_by_token(req.session_id, user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Telemetry
        asyncio.create_task(broadcast_event("TEXT_START", "Client Keyboard -> FastAPI", {"text": req.message}))
        
        # Crisis Check
        crisis = check_for_crisis(req.message)
        if crisis.is_crisis:
            self.repo.log_risk(session.id, user.id, crisis.trigger_phrase or req.message[:200], "AI intervened with extreme comfort.")
            self.repo.flag_session_crisis(session)

        # Async telemetry signals
        async def fast_telemetry():
            await broadcast_event("RAG_FETCH", "Fetching knowledge")
            await broadcast_event("MEMORY_FETCH", "Fetching cross-session memory")
            await broadcast_event("EMOTION_FETCH", "Analyzing tone")
            await broadcast_event("LLM_START", "Synthesizing Prompt -> LLM")
        asyncio.create_task(fast_telemetry())

        # History and Patterns
        past_msgs = self.repo.get_recent_messages(session.id)
        history = [{"role": m.role, "content": m.content} for m in past_msgs]
        history.append({"role": "user", "content": req.message})

        recent_user_msgs = [m.content for m in past_msgs if m.role == "user"][-5:]
        pattern_signal = analyze_patterns(recent_user_msgs, req.message)
        pattern_block = pattern_signal.as_prompt_block()

        # Persona & Context
        persona_summary = get_persona_summary(self.repo.db, user.id)
        rag_context = retrieve_context(req.message) if RAG_AVAILABLE else ""
        lang_prompt = get_language_prompt(req.language)

        # Emotion
        try:
            emotion = await asyncio.wait_for(detect_emotion(req.message), timeout=2.0)
        except Exception:
            emotion = detect_emotion_heuristic(req.message)

        tracker.update_emotion(session.id, emotion.label)
        tracker.record_message_length(session.id, len(req.message))
        if crisis.is_crisis:
            tracker.set_crisis_risk(session.id, "High")

        state = tracker.get_state(session.id)
        exercise_ctx = tracker.get_exercise_context(session.id)
        is_onboarding = state.is_onboarding
        case_file = tracker.get_case_file(session.id)

        # Assessor Phase
        if should_skip_assessor(req.message, case_file):
            case_file["runtime_state"]["decision"] = "RESPOND"
        else:
            try:
                case_file = await asyncio.wait_for(
                    assess_turn(
                        messages=history,
                        case_file=case_file,
                        user_message=req.message,
                        emotion_label=emotion.label,
                        rag_context=rag_context,
                        pattern_block=pattern_block,
                        persona_summary=persona_summary,
                    ),
                    timeout=15.0
                )
            except Exception as e:
                logger.error(f"[Assessor] Timed out or failed ({e}). Defaulting to RESPOND.")
                case_file["runtime_state"]["decision"] = "RESPOND"
            tracker.update_case_file(session.id, case_file)

        decision = case_file.get("runtime_state", {}).get("decision", "RESPOND")

        # Exercise Logic
        if decision == "GROUND":
            if exercise_ctx.get("state", "idle") == "idle":
                tracker.suggest_exercise(session.id, exercise_type="GROUNDING", triggered_by="assessor", pre_emotion=emotion.label)
                self.repo.suggest_exercise(session.id, user.id, "GROUNDING", emotion.label)
        elif decision == "EXERCISE_CONTINUE":
            if exercise_ctx.get("state", "idle") == "suggested":
                tracker.advance_exercise_state(session.id, "in_progress")
        elif decision == "EXERCISE_BREAK" or exercise_ctx.get("state", "idle") != "idle":
            tracker.reset_exercise(session.id)

        if exercise_ctx.get("state") == "awaiting_feedback":
            self.repo.complete_exercise(session.id, user.id, emotion.label, req.message)
            tracker.reset_exercise(session.id)

        # AI Generation
        current_exercise_state = tracker.get_state(session.id).exercise_state
        ai_response = await asyncio.to_thread(
            chat_with_maitri,
            messages=history,
            language=req.language,
            rag_context=rag_context,
            case_file=case_file,
            language_prompt=lang_prompt,
            is_crisis=crisis.is_crisis,
            exercise_phase=current_exercise_state,
        )
        await broadcast_event("LLM_DONE", "Response generated")

        # Persistence
        self.repo.save_messages(session.id, req.message, ai_response, req.language, emotion.label, emotion.score)

        # Persona Background Task
        total_user_msgs = len([m for m in past_msgs if m.role == "user"]) + 1
        if total_user_msgs % 5 == 0 or total_user_msgs == 1:
            # We defer updating persona (requires DB access so handled via the old async function)
            pass

        final_ex_state = tracker.get_state(session.id)
        return ChatResponse(
            response=ai_response,
            is_crisis=crisis.is_crisis,
            helplines=crisis.helplines if crisis.is_crisis else [],
            session_id=req.session_id,
            emotion=emotion.label,
            emotion_emoji=emotion.emoji,
            emotion_score=emotion.score,
            rag_used=bool(rag_context),
            exercise_state=final_ex_state.exercise_state,
            exercise_type=final_ex_state.active_exercise_type,
        )
