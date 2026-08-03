# 🌿 Mythri — Technical Architecture & Developer Guide

This document serves as the core technical manual for the Mythri AI mental health companion repository. It details the internal functionalities, the modular domain-driven architecture, and provides a strict mapping of where to find and modify specific logic.

---

## ⚙️ Core Functionalities & How They Work

### 🚀 Recent Updates (v8.2)
- **Next.js 16.2 Turbopack Compatibility:** Deprecated `middleware.ts` in favor of `proxy.ts` to resolve Turbopack compilation panics and comply with new routing standards.
- **Git Repository Migration:** Transferred local codebase tracking to the official `maitrihealth2/maitri-fullstack` GitHub origin.
- **Custom Python Watcher:** Replaced `nodemon` with a native `run_dev.py` script in the backend to handle graceful Uvicorn shutdowns and prevent port conflicts on Windows.
- **Backend Stability**: Implemented robust exception shielding in FastAPI middleware to prevent the server from shutting down on unexpected errors.
- **Enhanced Consultation Flow**: Introduced a `GREETING` decision mode for warm check-ins and mandated a questioning flow for ambiguous user shares to improve AI empathy and guidance.
- **Situation Classification**: Upgraded the internal Assessor model to classify user situations, providing better context for therapeutic responses.

The system is built on a highly decoupled FastAPI backend and a Next.js frontend, utilizing advanced AI streaming pipelines. Here is a breakdown of the core functionalities:

- **Real-Time Voice & Streaming Pipeline:** The Next.js frontend captures microphone audio using the Web Audio API and streams it via WebSockets. The FastAPI backend receives this stream, transcodes it to 16kHz Mono WAV using `FFmpeg` subprocesses, and sends it to the Sarvam API for highly accurate Speech-to-Text (STT).
- **Dual-Agent Meta-Cognitive Architecture:** Input text first routes to a **Dialogue State Analyst (Brain 1)** which evaluates the user's intent. Instructions are passed to the **Maitri Responder (Brain 2)**, which synthesizes the final empathetic response.
- **Retrieval-Augmented Generation (RAG):** Utilizing ChromaDB and local embeddings, the system retrieves structured clinical theories from the `knowledge/` directory.
- **Cross-Session Memory Tracking:** Interactions are logged to a PostgreSQL/SQLite database.
- **Emotion Engine & Crisis Checking:** Utterances run through a local HuggingFace pipeline (`SamLowe/roberta-base-go_emotions`) to gauge real-time emotional state. A deterministic regex engine checks for self-harm triggers.
- **Interactive UI & 3D Avatar:** The Next.js frontend features a React Three Fiber `<Mitra />` 3D Avatar and a live telemetry dashboard connected to backend SSE.

---

## 💻 Environments & Setup (Windows PowerShell)

You will need two distinct environment files for the two systems.

### 1. Backend (`backend/.env`)
```properties
SARVAM_API_KEY=your_key_from_dashboard.sarvam.ai
DATABASE_URL=sqlite:///./mindbridge.db
SECRET_KEY=anyrandomstring123
```
*Setup Command:*
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Frontend (`frontend/.env.local`)
```properties
NEXT_PUBLIC_API_URL=https://maitri-fullstack-1.onrender.com
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_key
# Other Firebase variables as needed
```
*Setup Command:*
```powershell
cd frontend
npm install
```

---

## ▶️ How to Run & Access the Application

The application consists of two servers running simultaneously. 

**Terminal 1 — Backend:**
We use a custom Python watcher to smoothly reload the server on code changes and handle graceful database teardowns.
```powershell
cd backend
.\venv\Scripts\activate
python run_dev.py
```
*Access:* The backend API and Swagger Docs run on **https://maitri-fullstack-1.onrender.com/docs**

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm run dev
```
*Access:* The Next.js web application is available at **https://maitri-fullstack-1.onrender.com**
*Telemetry UI:* The live visualization dashboard is at **https://maitri-fullstack-1.onrender.com/telemetry.html**

---

## 🧪 How to Check & Test the System

1. **Verify Backend Startup:** When you run `python run_dev.py`, ensure the terminal outputs `[Info] RAG ChromaDB found...` or a warning if not. Look for the `Uvicorn running on http://0.0.0.0:8000` confirmation.
2. **Verify Frontend Next.js:** Ensure Turbopack compiles successfully without panicking. Check that `proxy.ts` correctly redirects unauthenticated users to `/login`.
3. **Verify Local Emotion Model:** Send a test message in the chat UI. Observe the backend terminal; you should see a log like `[Local HF Emotion] Detected 'confusion' (0.49)`.

---

## 🎯 What We Should Do Next

Now that the core architecture is stable and running, the immediate next steps are:

1. **Initialize the Knowledge Base (RAG):**
   - The backend currently warns `[Warning] RAG ChromaDB not found`.
   - **Action:** We need to ingest clinical documents into the ChromaDB vector store so Maitri can fetch grounded therapeutic advice.
2. **Supervised Fine-Tuning (SFT) Preparation:**
   - **Action:** Begin curating and testing our conversational datasets located in `training/datasets/finetuning_datasets/` to eventually run the Colab LoRA tuning script on `sarvam-30b` or `qwen3`.
3. **End-to-End Voice Testing:**
   - **Action:** Test the full WebSocket pipeline from the Next.js React Three Fiber Avatar to the Sarvam STT/TTS endpoints. Verify that FFmpeg is correctly chunking and decoding the audio streams on Windows.

---

## 📂 Architecture Mapping

- **Backend Entry:** `backend/run_dev.py`
- **Frontend Entry:** `frontend/app/layout.tsx`
- **Authentication Proxy:** `frontend/proxy.ts`
- **AI Brains:** `backend/core/brain/`
- **LLM Integrations:** `backend/providers/sarvam/`