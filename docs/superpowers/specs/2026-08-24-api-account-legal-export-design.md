# API Account, Legal, and Export Design

## Goal

Expose the existing IZFIN account, versioned legal-consent, and user-data-export capabilities through the authenticated FastAPI boundary without changing Streamlit behavior or adding account deletion.

## Scope and constraints

- Work only from `develop` on `feat/api-account-legal-export`; never change `main`.
- Keep Streamlit as an existing consumer of the same framework-neutral services.
- Use Firebase Bearer identity for every endpoint that accesses or changes user data.
- Keep public legal-document reads separate from consent writes.
- Do not add account deletion, new persistence, queues, or new third-party dependencies.
- Preserve the `izfin-user-data-v1` export contract and return only the requesting user's data.

## Endpoint contracts

### Profile

`GET /api/v1/profile` requires a Firebase Bearer token. It returns the authenticated user's stored profile plus identity fields already supplied by Firebase when the profile does not contain them. A missing or unavailable user repository returns `503`; a missing profile is represented as an empty profile payload, not another user's data.

### Legal documents

`GET /api/v1/legal/terms` and `GET /api/v1/legal/privacy` are public. They return the currently configured document version and the same Markdown text used by Streamlit. The privacy response also carries the existing publication warning when data-controller settings are incomplete. The HTTP layer does not render Streamlit HTML.

### Consent

`GET /api/v1/legal/consent` requires a Firebase Bearer token. It reports the current terms and privacy versions and whether the stored profile accepts both versions.

`PUT /api/v1/legal/consent` requires a Firebase Bearer token and accepts two explicit booleans: `terms_accepted` and `privacy_notice_seen`. Both must be true; otherwise it returns HTTP `422` through Pydantic validation. It persists the existing versioned consent fields through the framework-neutral legal-consent service and returns the refreshed acceptance state. Repository failure returns `503` without masking an authorization failure.

### User export

`GET /api/v1/account/export` requires a Firebase Bearer token. It calls the existing account-data export workflow with the authenticated UID and e-mail, serializes the resulting package as JSON-compatible data, and returns `export_schema`, `exported_at`, and user documents. No data from another UID or e-mail is accepted from the request. A missing user repository returns `503`.

## Runtime composition

`ApiRuntime` gains configuration values for terms and privacy versions. `create_app` accepts those values with stable defaults suitable for tests, while production runtime composition reads the same environment configuration currently used by Streamlit. The router receives repository and version data only through `request.app.state.izfin_runtime`.

## Error behavior

- Missing or invalid Bearer tokens retain the existing authentication responses.
- A repository that is unavailable yields `503` with a Turkish user-safe message.
- Consent payloads that do not explicitly confirm both documents yield `422`.
- No endpoint accepts a UID or e-mail path/query/body override.
- Export does not set an attachment header in this slice; the web client receives the versioned JSON payload and chooses download presentation.

## Testing

Focused API tests will prove public legal documents, authenticated profile fallback, consent read/write with current versions, validation rejection, repository-unavailable `503`, and export owner isolation. Existing account-data and Streamlit AppTest suites remain part of the full regression gate. No Streamlit source is changed.

## Non-goals

- Account deletion and Firebase Auth token revocation.
- Export downloads/attachment headers, asynchronous exports, or bulk archival formats.
- A Next.js client or mobile client.
- Rate limiting, audit logging, OpenAPI/deployment documentation; these stay in the subsequent API hardening slice.
