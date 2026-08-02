import multiprocessing
import uvicorn
import os

if __name__ == "__main__":
    print("=============================================")
    print("   MindBridge Unified Backend Runner         ")
    print("=============================================")
    
    port = int(os.environ.get("PORT", 8000))
    env = os.environ.get("ENVIRONMENT", "production")
    
    # Calculate optimal workers for I/O bound tasks
    cores = multiprocessing.cpu_count()
    
    if env == "development":
        workers = 1
        print("[RUNNER] Development mode detected. Starting 1 worker.")
    else:
        workers = min((cores * 2) + 1, 8)
        print(f"[RUNNER] Production mode. Detected {cores} CPU cores. Starting {workers} workers.")
        
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
