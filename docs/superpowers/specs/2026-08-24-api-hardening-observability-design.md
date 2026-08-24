# API Hardening and Observability Design

## Goal

Add an HTTP-only protection and observability layer to IZFIN FastAPI while preserving every Streamlit workflow and keeping API contracts stable for future Next.js, mobile, and provider changes.

## Scope

- In-process rate limiting with identity/IP buckets and environment configuration.
- JSON structured request/error logging with request IDs and sensitive-data redaction.
- OpenAPI metadata, Bearer security documentation, and standard error responses.
- Deployment documentation for FastAPI, Firebase runtime credentials, CORS, rate limits, and multi-replica boundaries.

## Constraints

- Work on a `develop`-based feature branch only; never modify `main`.
- Do not modify `app2.py` or Streamlit runtime behavior.
- Do not add Redis, Celery, a database, or a third-party logging dependency.
- Do not log Authorization headers, bearer tokens, Firebase claims, e-mail values, request bodies, or export payloads.
- The limiter is per-process; production multi-replica deployments must apply an edge/WAF/shared-store limiter separately.

## Request context and logging

`RequestContextMiddleware` resolves an incoming `X-Request-ID` only when it is a bounded safe token; otherwise it generates a UUID. It writes the ID to the response header and stores it on request state.

Every request produces one JSON log event containing request ID, method, normalized route template, status code, elapsed milliseconds, and a privacy-safe client identifier category. Exception logs include request ID and exception class only. Log records do not include arbitrary headers, query values, bodies, user e-mail, or data payloads. Existing Sentry configuration remains optional and is not initialized by this layer.

## Rate limiting

`RateLimitMiddleware` runs before router work. It skips `/api/v1/health`, `/api/v1/health/ready`, `/docs`, `/openapi.json`, and `/redoc`. For authenticated routes, it uses the resolved Firebase UID after bearer verification where available; for public/no-identity routes, it uses a normalized client IP (honoring `X-Forwarded-For` only when an explicit trusted-proxy setting is enabled).

The default limiter uses a bounded in-memory fixed window. Environment settings configure enablement, maximum requests, and window seconds. Endpoint costs are uniform in this slice. An exhausted bucket returns HTTP `429`, JSON detail `"İstek sınırına ulaşıldı. Lütfen kısa süre sonra tekrar deneyin."`, `Retry-After`, and `X-Request-ID`.

## OpenAPI

The app factory supplies API title, description, contact-free version, and Bearer HTTP security documentation. Protected endpoint contracts declare HTTP `401`, `429`, and `503` response shapes. OpenAPI remains served at the normal FastAPI endpoints and exposes no secret configuration.

## Deployment documentation

The README gains a FastAPI deployment section covering: uvicorn command; Firebase service account JSON/file variables; Finnhub/provider configuration as runtime-injected adapters; CORS origin configuration; all hardening variables; health/readiness probing; log format; and the requirement to use an upstream rate limit for multiple replicas. It states explicitly that Streamlit remains independently deployable and operational.

## Testing

Focused tests cover generated/preserved request IDs, log redaction, 429 and retry header behavior, distinct public-client buckets, health exemption, OpenAPI security/error documentation, and environment parsing. Full pytest, Streamlit AppTest, compileall, diff checks, PR CI, and post-merge develop CI remain required.

## Non-goals

- Persistent or distributed rate-limit counters.
- User-facing analytics, log storage, audit trails, or Sentry initialization changes.
- Provider migration implementation; providers remain runtime adapters.
- Next.js UI implementation or Streamlit replacement.
