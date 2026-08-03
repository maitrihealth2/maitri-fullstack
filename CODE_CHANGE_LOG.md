# Code Change Log

This file summarizes the codebase updates made in the current session.

## Summary of Changes

### Backend
- `backend/app.py`
  - Added a lightweight `/up` endpoint for health checks.
  - Kept `/ready` for readiness readiness checks.
  - Retained background RAG knowledge base build logic for `RAG_AUTO_BUILD=true`.

- `backend/main.py`
  - Removed import-time RAG initialization and startup blocking checks.
  - Simplified Uvicorn startup flow so the app starts without waiting on the knowledge base.

- `backend/modules/consultation/api.py`
  - Removed import-time RAG database build.
  - Switched to runtime readiness checks using `is_knowledge_base_ready()`.
  - Prevented `retrieve_context()` from being called unless RAG is ready.

- `backend/modules/voice/api.py`
  - Removed import-time RAG build logic.
  - Avoided RAG initialization on import.

- `backend/rag/knowledge/retriever.py`
  - Added a readiness guard in `retrieve_context()` so missing knowledge bases return an empty context cleanly.

- `backend/src/modules/consultation/services.py`
  - Updated legacy service RAG import handling to avoid startup failures when RAG is unavailable.

### Deployment
- `deployment/render/render.yaml`
  - Changed health check path to `/up`.
  - Reduced backend instance count to `1` for hobby-level runtime.

### Frontend
- `frontend/core/firebase.ts`
  - Removed dummy Firebase fallback configuration.
  - Added a real Firebase configuration guard.
  - Exported `isFirebaseConfigured` so the app can disable Google sign-in when Firebase is not setup.

- `frontend/modules/authentication/frontend/page.tsx`
  - Added a disabled Google button state when Firebase is not configured.
  - Added a warning message explaining why Google Sign-In is unavailable.

## Notes
- A local commit was created for these changes.
- A push to `origin/production-security-overhaul` was attempted, but the remote contains new commits that must be pulled first.
