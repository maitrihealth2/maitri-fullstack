import uvicorn
import os

if __name__ == "__main__":
    print("=============================================")
    print("   MindBridge Unified Backend Runner         ")
    print("=============================================")
    
    port = int(os.environ.get("PORT", 8000))
    env = os.environ.get("ENVIRONMENT", "production")
    web_concurrency = os.environ.get("WEB_CONCURRENCY")

    if env == "development":
        print("[RUNNER] Development mode detected. Starting single process server.")
    elif web_concurrency:
        try:
            workers = max(1, int(web_concurrency))
            print(f"[RUNNER] WEB_CONCURRENCY detected ({workers}). Running in single-process mode for container stability.")
        except ValueError:
            print("[RUNNER] Invalid WEB_CONCURRENCY value. Running single-process server.")
    else:
        print("[RUNNER] No WEB_CONCURRENCY set. Running single-process server for container stability.")

    print(f"[RUNNER] Starting Uvicorn Server on port {port}...")

    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
        timeout_keep_alive=60,
        limit_concurrency=1000,
        log_level="info"
    )
