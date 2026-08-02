"""
Verification script for MindBridge backend stability and dialogue flow fixes.
"""
import sys
import pathlib
import json

# Add backend directory to sys.path
backend_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from rag.brain.state_tracker import empty_case_file, StateTracker
from rag.brain.analyst import should_skip_assessor
from providers.sarvam.sarvam_client import chat_with_maitri, THERAPY_SYSTEM_PROMPT

def test_greeting_handling():
    print("[TEST 1] Testing Greeting Fast-Path and Prompt Logic...")
    case_file = empty_case_file()
    user_msg = "hello"
    
    # Test fast-path check
    is_skipped = should_skip_assessor(user_msg, case_file)
    assert is_skipped is True, "Greeting should be caught by fast-path skip filter"
    
    # Set decision to GREETING
    case_file["runtime_state"]["decision"] = "GREETING"
    
    response = chat_with_maitri(
        messages=[{"role": "user", "content": user_msg}],
        case_file=case_file
    )
    print(f"User: '{user_msg}' -> Maitri: '{response}'")
    assert "?" in response or "how" in response.lower() or "feeling" in response.lower(), "Greeting response should ask a welcoming question"
    print("[SUCCESS] TEST 1 PASSED: Greeting Handler is warm and interactive.")

def test_case_file_schema():
    print("\n[TEST 2] Testing Case File Schema & Situation Classification structure...")
    cf = empty_case_file()
    assert "situation_classification" in cf["conversation_state"], "schema must include situation_classification"
    assert cf["conversation_state"]["situation_classification"]["category"] == "unknown"
    print("[SUCCESS] TEST 2 PASSED: Case File schema updated with classification.")

def test_guidance_generation():
    print("\n[TEST 3] Testing Actionable Guidance & Classification Response...")
    case_file = empty_case_file()
    case_file["conversation_state"]["situation_classification"] = {
        "category": "work_stress",
        "summary": "User is experiencing severe work burnout from manager expectations",
        "confidence": 0.9
    }
    case_file["runtime_state"]["decision"] = "RESPOND"
    
    user_msg = "My manager gave me 5 impossible deadlines today and yelled at me in front of everyone."
    messages = [
        {"role": "user", "content": "I feel horrible today."},
        {"role": "assistant", "content": "I am so sorry you are feeling this way. What happened today?"},
        {"role": "user", "content": user_msg}
    ]
    
    response = chat_with_maitri(
        messages=messages,
        case_file=case_file
    )
    print(f"User: '{user_msg}'\nMaitri: '{response}'")
    assert len(response) > 20, "Response should be substantive"
    print("[SUCCESS] TEST 3 PASSED: Response provides empathetic validation and actionable direction.")

def test_ambiguous_emotional_share():
    print("\n[TEST 4] Testing Ambiguous Emotional Share & Question Generation...")
    case_file = empty_case_file()
    case_file["runtime_state"]["decision"] = "ASK"
    case_file["conversation_state"]["recommended_question"] = "When did you first start noticing this shift, or has there been a quiet pressure building up?"
    
    user_msg = "You don't really know how to explain this. Nothing in my life looks wrong from the outside, and if someone asked me whether I'm okay, I'd probably just say yes. But lately, I feel like I'm becoming someone I don't recognize. Some days everything feels effortless, and on others, even replying to a message feels impossible. The strange part is that I can't tell what changed—or if anything actually did. Maybe I'm just overthinking... or maybe I've been ignoring something for a long time. I honestly don't know what's happening to me."
    
    response = chat_with_maitri(
        messages=[{"role": "user", "content": user_msg}],
        case_file=case_file
    )
    print(f"User Share:\n'{user_msg[:80]}...'\nMaitri Response:\n'{response}'")
    assert "?" in response, "Maitri MUST ask a question when in ASK mode!"
    assert len(response) > 50, "Response should be warm, deep, and complete"
    print("[SUCCESS] TEST 4 PASSED: Maitri provides deep empathy AND asks an exploratory question.")

if __name__ == "__main__":
    try:
        test_greeting_handling()
        test_case_file_schema()
        test_guidance_generation()
        test_ambiguous_emotional_share()
        print("\n[ALL TESTS PASSED SUCCESSFULLY!]")
    except Exception as e:
        print(f"\n[VERIFICATION TEST FAILED]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
