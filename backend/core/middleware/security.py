import time
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger("security")

# Simple In-Memory Rate Limiter (Token Bucket / Fixed Window)
# Format: {ip_address: (count, reset_time)}
RATE_LIMIT_STORE: Dict[str, Tuple[int, float]] = {}
DEFAULT_RATE_LIMIT = 100  # requests per minute
AUTH_RATE_LIMIT = 10      # requests per minute for auth routes
RATE_LIMIT_WINDOW = 60    # 60 seconds

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_payload_bytes: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_payload_bytes = max_payload_bytes

    async def dispatch(self, request: Request, call_next):
        # 1. Payload Size Limit
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_payload_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Payload too large. Maximum size is 10MB."}
                    )
            except ValueError:
                pass
        
        # 2. Rate Limiting
        # In a proxied setup (Nginx), request.client.host is the internal Docker IP
        # We must use X-Forwarded-For or X-Real-IP
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = request.headers.get("x-real-ip")
        
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif real_ip:
            client_ip = real_ip
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        path = request.url.path
        
        current_time = time.time()
        
        # Select limit based on path
        limit = AUTH_RATE_LIMIT if path.startswith("/api/auth/") else DEFAULT_RATE_LIMIT
        
        # Clean up old entries to prevent memory leak (simplified for in-memory)
        # In a real distributed prod, we'd use Redis
        if client_ip in RATE_LIMIT_STORE:
            count, reset_time = RATE_LIMIT_STORE[client_ip]
            if current_time > reset_time:
                RATE_LIMIT_STORE[client_ip] = (1, current_time + RATE_LIMIT_WINDOW)
            else:
                if count >= limit:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip} on path {path}")
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please try again later."}
                    )
                RATE_LIMIT_STORE[client_ip] = (count + 1, reset_time)
        else:
            RATE_LIMIT_STORE[client_ip] = (1, current_time + RATE_LIMIT_WINDOW)
        
        # 3. Process Request
        response = await call_next(request)
        
        # 4. Inject Security Headers
        # We only inject HSTS here; Nginx handles X-Frame-Options and XSS Protection.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        
        return response
