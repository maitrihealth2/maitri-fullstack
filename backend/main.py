import multiprocessing
import uvicorn
import os

if __name__ == "__main__":
    print("=============================================")
    print("   MindBridge Unified Backend Runner         ")
    print("=============================================")
    
    port = int(os.environ.get("PORT", 8000))
    env = os.environ.get("ENVIRONMENT", "production")
    web_concurrency = os.environ.get("WEB_CONCURRENCY")
    
    # Calculate optimal workers for I/O bound tasks
    cores = multiprocessing.cpu_count()
    if env == "development":
        workers = 1
        print("[RUNNER] Development mode detected. Starting 1 worker.")
    elif web_concurrency:
        try:
            workers = max(1, int(web_concurrency))
            print(f"[RUNNER] WEB_CONCURRENCY detected. Starting {workers} worker(s).")
        except ValueError:
            workers = 1
            print("[RUNNER] Invalid WEB_CONCURRENCY value. Falling back to 1 worker.")
    else:
        workers = 1
        print(f"[RUNNER] No WEB_CONCURRENCY set. Defaulting to 1 worker for container stability.")
        
    print(f"[RUNNER] Starting Uvicorn Server on port {port}...")

    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
        workers=workers,
        timeout_keep_alive=60,
        limit_concurrency=1000,
        log_level="info"
    )
