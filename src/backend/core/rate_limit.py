import hashlib

from fastapi import HTTPException, Request, status

from backend.core.audit import request_details


async def enforce_rate_limit(request: Request, namespace: str, identity: str, *, limit: int, window_seconds: int) -> None:
    ip_address, _ = request_details(request)
    ip_fingerprint = hashlib.sha256((ip_address or "unknown").encode()).hexdigest()
    identity_fingerprint = hashlib.sha256(identity.casefold().encode()).hexdigest()
    keys = (f"rate:{namespace}:ip:{ip_fingerprint}", f"rate:{namespace}:identity:{identity_fingerprint}")
    redis = request.app.state.redis
    try:
        exceeded = False
        for key in keys:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            exceeded = exceeded or count > limit
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is temporarily unavailable") from exc
    if exceeded:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please try again later.")
