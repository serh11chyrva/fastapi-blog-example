import hashlib

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from backend.audit.dependencies import request_details
from backend.core.resources import get_resources


RATE_LIMIT_SCRIPT = """
local exceeded = 0
for _, key in ipairs(KEYS) do
    local count = redis.call('INCR', key)
    if redis.call('TTL', key) < 0 then
        redis.call('EXPIRE', key, ARGV[2])
    end
    if count > tonumber(ARGV[1]) then
        exceeded = 1
    end
end
return exceeded
"""


async def enforce_rate_limit(
    request: Request,
    namespace: str,
    identity: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Count both dimensions atomically and repair counters missing an expiry."""
    ip_address, _ = request_details(request)
    ip_fingerprint = hashlib.sha256((ip_address or "unknown").encode()).hexdigest()
    identity_fingerprint = hashlib.sha256(identity.casefold().encode()).hexdigest()
    keys = (f"rate:{namespace}:ip:{ip_fingerprint}", f"rate:{namespace}:identity:{identity_fingerprint}")
    redis = get_resources(request).redis
    try:
        exceeded = await redis.eval(RATE_LIMIT_SCRIPT, len(keys), *keys, limit, window_seconds)
    except RedisError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is temporarily unavailable") from exc
    if exceeded:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please try again later.")
