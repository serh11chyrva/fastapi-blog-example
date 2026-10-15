"""Extract audit metadata at the HTTP boundary."""

from typing import Annotated

from fastapi import Depends, Request

from backend.audit.context import AuditContext


def audit_context(request: Request) -> AuditContext:
    # The application is reached through a proxy that overwrites X-Real-IP.
    return AuditContext(
        ip_address=request.headers.get("x-real-ip") or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent", "")[:512] or None,
    )


def request_details(request: Request) -> tuple[str | None, str | None]:
    context = audit_context(request)
    return context.ip_address, context.user_agent


Audit = Annotated[AuditContext, Depends(audit_context)]
