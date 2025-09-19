# EDI Trading Partner Self-Service Portal Specification

## 1. Document Control
- Version: 0.1 (Draft)
- Date: 2025-09-16
- Owner: Integration Platform Team
- Status: Draft for review

## 2. Executive Summary
Build an Azure-hosted, secure self-service portal enabling external EDI trading partners to manage connectivity credentials (PGP public/private key pairs and SFTP password) and monitor EDI file transfer & processing status. Frontend: latest Angular. Backend: C# ASP.NET Core (.NET 9 when GA) with OpenAPI, hosted in Azure App Service (Linux). Single deployment hosting both API and compiled Angular SPA (served as static assets). Authentication & authorization: Microsoft Entra External ID for B2B / external partner federation. Initial scope emphasizes credential lifecycle management and visibility (dashboard) without allowing partners to alter core mapping/translation logic.

## 3. Scope
### In Scope
- Partner authentication via Entra External ID (user flows: sign-in, password reset / federation).
- Role-based authorization (PartnerUser, PartnerAdmin, InternalSupport).
- Self-service PGP key management: upload existing public key, generate new key pair (server-side), view fingerprints, revoke/rotate keys.
- Download of generated private key exactly once post-generation (ephemeral cache + secure transport).
- SFTP password reset (write-only: partner submits new password or triggers secure random generation + display once).
- Monitoring dashboard: inbound/outbound file statuses, processing pipeline stages, success/error counts, recent failures, SLA timers.
- Charts: daily file counts (in/out), transaction counts (e.g., 850/810 etc. configurable), success vs failure ratio, average processing latency.
- Error detail drill-down (non-sensitive): file name, correlation ID, timestamps, error category, remediation hint.
- Mock backend service layer & storage abstraction (no real EDI integration in MVP) with seeded sample data.
- OpenAPI documented endpoints, Swagger UI in non-production.
- Audit logging of credential operations & sensitive downloads.
- Infrastructure environments: Dev, Test, Prod.

### Out of Scope (Phase 1)
- Real AS2 / VAN / SFTP transfer orchestration.
- EDI translation/mapping configuration changes by partners.
- Multi-tenant white-label branding per partner.
- Notification center / email alerts (candidate for Phase 2).
- Fine-grained per-transaction drill-down (beyond high-level metadata) containing PHI/PCI (excluded entirely).

## 4. Personas
- Partner User: Operates day-to-day, views dashboard, can request password reset, view keys (public metadata only), initiate key generation.
- Partner Admin: All Partner User abilities + upload/revoke keys, approve password reset, view audit entries for their organization.
- Internal Support (read-only extended): Troubleshoot, view broader error context, cannot download partner private keys after initial generation.
- System Automation (service principal): Future use for API-to-API integration (not Phase 1, placeholder scope).

## 5. User Stories (Selected)
| ID | As a | I want | So that |
|----|------|--------|---------|
| US-001 | Partner User | To authenticate with my org identity | I can securely access resources |
| US-002 | Partner Admin | Upload my existing PGP public key | Files can be encrypted for me |
| US-003 | Partner Admin | Generate a new PGP key pair | I can rotate keys without external tools |
| US-004 | Partner Admin | Download the private key once | I can install it on our SFTP server securely |
| US-005 | Partner Admin | View key fingerprint & creation date | I can verify distribution consistency |
| US-006 | Partner Admin | Revoke an old key | Prevent future encryption with compromised key |
| US-007 | Partner User | Request SFTP password rotation | Improve security periodically |
| US-008 | Partner Admin | Auto-generate a strong SFTP password | Maintain complexity standards |
| US-009 | Partner User | View recent file transfer statuses | Confirm successful exchanges |
| US-010 | Partner User | See error counts & categories | Prioritize remediation |
| US-011 | Partner User | Filter dashboard by date range & direction | Focus on relevant data |
| US-012 | Internal Support | View audit log of credentials ops | Investigate issues |
| US-013 | Partner Admin | Receive confirmation after key rotation | Ensure action completion |
| US-014 | Partner User | Drill into a failed file | Understand failure cause |
| US-015 | Partner Admin | See processing latency KPI | Detect performance degradation |

## 6. Functional Requirements
### 6.1 Authentication & Authorization
- FR-Auth-01: Entra External ID user flows configured (sign-in, password reset, multi-factor optional policy hook).
- FR-Auth-02: JWT access token validation in API (Microsoft.Identity.Web).
- FR-Auth-03: Role claims mapped from Entra groups (configurable mapping service).

### 6.2 PGP Key Management

- FR-Key-01: Upload endpoint accepts ASCII-armored public key, validates format & key length (>= 2048 RSA) & uniqueness (no duplicate fingerprint per partner).
- FR-Key-02: Server-side key generation supports RSA 4096 (default) using isolated process (e.g., BouncyCastle) and returns private key only once.
- FR-Key-03: Store public key + metadata (fingerprint, created, validFrom, validTo optional, status: PendingActivation/Active/Revoked/Expired/Superseded) and `isPrimary` flag.
- FR-Key-04: Audit entry recorded for create/upload/revoke/download/promote/demote.
- FR-Key-05: Revocation sets status to Revoked; encryption selection must exclude revoked/expired.
- FR-Key-06: Allow multiple Active keys simultaneously during rotation overlap window (configurable, default 30 days) to support gradual migration.
- FR-Key-07: Exactly one Primary key per partner used for outbound encryption; others Active keys usable only for inbound decryption.
- FR-Key-08: Future-dated activation supported via `validFrom`; keys remain PendingActivation until time reached.
- FR-Key-09: Optional `validTo` triggers automatic Expired transition via background job.
- FR-Key-10: Setting a new Primary automatically demotes prior Primary (both audited).
- FR-Key-11: Superseded status assigned when key replaced intentionally prior to `validTo` and still needs limited inbound acceptance until overlap window ends.

### 6.3 SFTP Password Management

- FR-SFTP-01: Partners may either submit a new password (complexity policy) or request auto-generation.
- FR-SFTP-02: Auto-generated password length >= 24 chars with upper/lower/digit/special.
- FR-SFTP-03: Password stored salted & hashed (Argon2id) not retrievable in plaintext.
- FR-SFTP-04: Display generated password exactly once (ephemeral response) then discard plaintext.
- FR-SFTP-05: Audit entry for change including initiator & method (manual/auto).

### 6.4 Dashboard & Monitoring

- FR-Dash-01: Summary KPIs: Inbound Files (24h), Outbound Files (24h), Success Rate %, Avg Processing Time (last 24h), Open Errors Count.
- FR-Dash-02: Time-series chart: per-hour file counts past 48h.
- FR-Dash-03: Pie / Donut: Success vs Failed vs Pending (last 24h).
- FR-Dash-04: Top 5 Error Categories table.
- FR-Dash-05: Recent Failed Files table with pagination.
- FR-Dash-06: Drill-down includes file metadata: fileId, partnerId, direction, docType, size, receivedAt, processedAt, status, correlationId, errorCode, errorMessage (sanitized), retryCount.
- FR-Dash-07: Filter controls: date range (max 90 days), direction, docType, status.

### 6.5 Audit & Logging

- FR-Audit-01: Persist credential operation events (key upload, key generate, key revoke, private key download, password change) with timestamp, actor, partnerId, operationType, successFlag.
- FR-Audit-02: Internal Support read-only API to paginate audit events with filters.

### 6.6 Mock Data Services (Phase 1)

- FR-Mock-01: In-memory or lightweight store (e.g., EF Core InMemory) seeded with sample partners, keys, file transfer events.
- FR-Mock-02: Deterministic sample dataset generator for consistent front-end development.
- FR-Mock-03: Ability to toggle mock persistence to file (JSON) via config for local dev.

### 6.7 OpenAPI

- FR-API-01: All endpoints described with OpenAPI 3.1, grouped tags (Auth, Keys, SFTP, Dashboard, Audit).
- FR-API-02: JSON:API style error envelope (code, message, traceId) consistent.
- FR-API-03: Pagination standard query params: `page`, `pageSize` (max 100), `sort`.

### 6.8 Real-Time Updates (Server-Sent Events)

- FR-SSE-01: Provide a unidirectional Server-Sent Events (SSE) endpoint at `GET /events/stream` emitting updates for new file transfer events, status changes, and key lifecycle changes (promote/revoke) relevant to the authenticated partner.
- FR-SSE-02: Events formatted as `event: <type>\n id: <seq>\n data: <json>\n\n` with types: `file.created`, `file.statusChanged`, `key.promoted`, `key.revoked`, `dashboard.metricsTick`.
- FR-SSE-03: Reconnect guidance: client uses `Last-Event-ID` header to resume sequence; server maintains rolling in-memory event buffer (minimum last 500 events per partner or 15 minutes, whichever greater).
- FR-SSE-04: Heartbeat comment `:hb` every 15s of inactivity to keep connection alive.
- FR-SSE-05: Authorization: same JWT bearer token; connection closed if token expires (client must refresh & reconnect).
- FR-SSE-06: Backpressure: limit max concurrent SSE connections per partner (default 3) returning HTTP 429 if exceeded.
- FR-SSE-07: SSE endpoint excluded from OpenAPI schema (documented separately) to avoid tooling noise; reference in developer docs.
- FR-SSE-08: Graceful degradation: if browser/EventSource unsupported, frontend falls back to periodic (60s) polling of summary + recent files.

## 7. Non-Functional Requirements

- NFR-Security-01: All traffic HTTPS enforced; HSTS enabled.
- NFR-Security-02: No private keys stored after delivery (only encrypted-at-rest ephemeral temp storage < 5 min TTL).
- NFR-Performance-01: Dashboard aggregate requests < 1.5s p95 with 10k file records dataset (mock baseline).
- NFR-Scalability-01: Horizontal scaling via App Service plan scale-out; stateless API design.
- NFR-Availability-01: Target 99.5% (Phase 1) - single region; roadmap multi-region active-active.
- NFR-Observability-01: Structured logging (Serilog) + distributed tracing (W3C Trace Context) integrated with Azure Application Insights.
- NFR-Compliance-01: No storage of PHI/PCI; classified as low sensitivity dataset.
- NFR-UX-01: Responsive design supporting desktop & tablet (mobile read-only acceptable Phase 1).
- NFR-Internationalization-01: English only Phase 1; design for i18n readiness.
- NFR-Maintainability-01: Linting & formatting pipelines (ESLint, Prettier, dotnet analyzers) required passing build.

## 8. System Architecture Overview

High-level components:
- Angular SPA (static) served from ASP.NET Core `wwwroot` after `ng build` output integrated pipeline.
- C# ASP.NET Core API (Controllers/Minimal APIs) exposing credential, dashboard, audit endpoints.
- Entra External ID for identity; tokens validated by API middleware.
- (Future) EDI Processing Engine (placeholder not implemented) – mocked by data generation service.
- Key Generation Service (wrapper around BouncyCastle / .NET cryptography) isolated.
- Audit Log Store (in-memory initially) abstracted via repository interface.
- Server-Sent Events Dispatcher (in-memory event bus fan-out per partner; future upgrade path to persistent queue / Azure Event Grid).


Sequence (PGP generation): User -> Angular -> API `POST /api/keys/generate` -> KeyGen service -> store public key metadata -> private key ephemeral cache -> response -> ephemeral cache purge job.

## 9. Azure Components (Initial)

- Azure App Service (Linux) – hosts API + SPA.
- Azure Entra External ID tenant / app registrations (Frontend SPA, Backend API scopes).
- Azure Application Insights – telemetry & logs.
- Azure Key Vault (Phase 1 limited) – store signing secrets (JWT), encryption keys for ephemeral private key at-rest (if disk swap used).
- Azure Storage (Phase 2) – persistent file metadata & dashboards at scale.
- Azure API Management (Phase 2) – external facade + throttling.

## 10. Security & Identity

- Entra External ID single-tenant or multi-tenant configuration with redirect URIs for SPA (auth code + PKCE flow).
- Access token scopes: `api://<backend-app-id>/.default` with roles claim mapping.
- RBAC mapping table maintained in configuration.
- Private key delivery uses Content-Disposition attachment; response flagged `no-store` caching headers.
- CSP headers restricting script sources to self + specific CDNs if required.
- CORS restricted to approved portal domain(s).
- Rate limiting middleware (basic sliding window) for credential endpoints.
- Anti-automation: reCAPTCHA (optional) for password rotation & key generation (Phase 2 consideration).

## 11. Key & Password Management Details

### PGP Key Generation / Rotation Flow

1. Validate user role (PartnerAdmin).
2. Accept optional `validFrom` (defaults now), optional `validTo`, and `makePrimary` flag.
3. Generate RSA 4096 key pair.
4. Persist key: if `validFrom` > now set status PendingActivation else Active.
5. If `makePrimary=true` or no existing primary, set new key primary and demote old primary (audit both actions).
6. Return private key (ASCII-armored) once; ephemeral memory purge after response or max 60s.
7. Background sweeper transitions PendingActivation -> Active and Active -> Expired; auto-promote latest Active if primary expired (configurable).
8. Prior primary enters Superseded state for configured overlap window (default 30 days) before optional revoke.
9. Revocation immediately disables key (inbound/outbound); if revoked primary, promote most recent eligible Active key.

### SFTP Password Flow

1. User requests manual or auto-generation.
2. If auto: cryptographically secure RNG produce password, complexity enforced by regex + entropy check.
3. Hash with Argon2id (configured memory/time cost) -> store hash + salt.
4. Return password in response (once) with disclaimers.

## 12. Data Model (Logical)

### Partner

- partnerId (GUID)
- name
- status (Active/Suspended)
- createdAt

### PgpKey

- keyId (GUID)
- partnerId (FK)
- publicKeyArmored (string)
- fingerprint (string)
- algorithm (string)
- keySize (int)
- createdAt
- validFrom (datetime)
- validTo (nullable datetime)
- revokedAt (nullable datetime)
- status (PendingActivation/Active/Revoked/Expired/Superseded)
- isPrimary (bool)

### SftpCredential

- partnerId (PK/FK)
- passwordHash
- passwordSalt
- lastRotatedAt
- rotationMethod (Manual/Auto)

### FileTransferEvent

- fileId (GUID)
- partnerId
- direction (Inbound/Outbound)
- docType (string)
- sizeBytes (int)
- receivedAt
- processedAt (nullable)
- status (Pending/Processing/Success/Failed)
- correlationId
- errorCode (nullable)
- errorMessage (nullable sanitized)
- retryCount (int)
- processingLatencyMs (computed)

### AuditEvent

- auditId (GUID)
- partnerId
- actorUserId
- actorRole
- operationType (KeyUpload|KeyGenerate|KeyRevoke|KeyDownload|SftpPasswordChange)
- timestamp
- success (bool)
- metadata (JSON)

## 13. API Endpoints (Draft)

Base path: `/api`

| Method | Path | Purpose | Auth Role |
|--------|------|---------|----------|
| GET | /health | Liveness | None |
| GET | /version | Build/version info | None |
| GET | /keys | List active & historical keys | PartnerUser |
| POST | /keys/upload | Upload public key | PartnerAdmin |
| POST | /keys/generate | Generate new key pair (returns private key) | PartnerAdmin |
| POST | /keys/{keyId}/revoke | Revoke key | PartnerAdmin |
| GET | /sftp/credential | Get metadata (no password) | PartnerUser |
| POST | /sftp/credential/rotate | Rotate password (manual or auto) | PartnerAdmin |
| GET | /dashboard/summary | KPI aggregates | PartnerUser |
| GET | /dashboard/timeseries | File counts over time | PartnerUser |
| GET | /dashboard/errors/top | Top error categories | PartnerUser |
| GET | /files | List file events (filters) | PartnerUser |
| GET | /files/{fileId} | File detail | PartnerUser |
| GET | /audit | Audit events (restricted) | InternalSupport |

Common Query Parameters:

- Pagination: `page` (default 1), `pageSize` (default 25, max 100)
- Sorting: `sort` (e.g., `receivedAt:desc`)
- Filters (files): `direction`, `status`, `docType`, `dateFrom`, `dateTo`.

Error Response Schema:

```json
{
  "error": {
    "code": "KEY_CONFLICT",
    "message": "An active key already exists",
    "traceId": "00-<trace>"
  }
}
```

## 14. Frontend (Angular) Architecture

- Angular latest LTS (v18 if available at implementation time).
- Standalone component architecture, signal-based state management (if stable), else NgRx for global slices (auth, dashboard, keys, files, audit).
- Core Modules: Auth, Layout, Dashboard, Keys, Sftp, Files, Audit, Shared (UI components), Api (HTTP clients typed via OpenAPI codegen).
- Lazy loading for feature routes to optimize initial bundle.
- Interceptors: Auth token attach, Error mapping, Loading indicator, Retry (idempotent GET only).
- Theming: Angular Material baseline with custom palette (accessibility AA contrast).
- Charting: ngx-charts or Apache ECharts wrapper (evaluate bundle size) for time-series & pie charts.

## 15. Dashboard Metrics & Aggregation Strategy (Mock Phase)

- Precompute aggregates on request from in-memory dataset (LINQ groupings).
- Simulate latency variance with optional delay injection (dev only) to test skeleton loaders.
- Provide deterministic seed so charts stable unless a `?seed=timestamp` flag triggers regeneration.
- Optional SSE push of incremental KPI deltas every 30s (mock) to reduce full refresh calls.

## 16. Mock Service Strategy

- Dedicated `IMockDataSeeder` run at startup (dev/test) populating: 5 partners, 2 keys each (1 active), 500 file events mixed statuses.
- Abstraction Interfaces: `IKeyRepository`, `ISftpCredentialRepository`, `IFileEventRepository`, `IAuditRepository`.
- Use EF Core InMemory provider; repository returns `IQueryable` for filtering/pagination service layer.
- Feature flags via appsettings: `UseMockData = true` gating seeding pipeline.

## 17. Deployment & Environments

- Build pipeline: CI triggers on main + PR; steps: dotnet restore/build/test, ng build --configuration=production, copy dist to `wwwroot`, publish artifact.
- Release: Deploy to App Service using `az webapp deploy` or GitHub Actions `azure/webapps-deploy`.
- Configuration via App Service settings: connection strings (future), feature flags, AllowedOrigins.
- Slot strategy: Staging slot for smoke tests before swap to production (Phase 1 optional).

## 18. Observability

- Application Insights SDK auto-collection (requests, dependencies, traces, exceptions) + custom events (`KeyGenerated`, `PasswordRotated`).
- Correlation: TraceId surfaced in error envelope to front-end.
- Dashboards in Azure Portal for request performance & failure rate.
- Track SSE connection opens/closes, average duration, reconnect rate metrics.

## 19. Testing Strategy

- Backend: Unit tests for services (key generation, validation), repository tests (in-memory), contract tests verifying OpenAPI schema stability.
- Frontend: Component tests (Jest), E2E smoke (Playwright) for critical flows (login mock, key generation, dashboard load).
- Security tests: Lint OpenAPI for auth on protected routes.

## 20. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Private key leakage | High | One-time delivery, memory wipe, no persistence |
| Weak password generation | Med | Use cryptographically secure RNG + entropy tests |
| Excessive dashboard query cost at scale | Med | Introduce pre-aggregated store Phase 2 |
| Role misconfiguration in Entra | Med | Automated startup validation & health checks |
| Large file dataset performance | Med | Add indexed persistent storage Phase 2 |
| SSE connection storm / resource exhaustion | Med | Limit concurrent connections + heartbeat timeouts |
| Missed events after reconnect | Low | Support Last-Event-ID resume with rolling buffer |

## 21. Backlog (Future Enhancements)

- Email / webhook notifications on failures.
- Multi-region active-active with traffic manager.
- API Management fronting with subscription keys & throttling.
- Partner self-registration workflow (approval gate).
- Key expiration policies & reminders.
- Upgrade SSE to multi-node scalable distribution (e.g., Redis pub/sub or Azure Event Grid integration).
- Enhanced analytics (doc type success trendlines, SLA breach alerts).

## 22. Open Questions

- Will SFTP endpoint management (host/port) also be exposed to partners? (Currently no.)
- Required retention period for audit events? (Default placeholder 365 days.)
- Do we need multi-language UI in near term? (Assumed not.)
- Should password rotations enforce minimum interval? (Not defined.)

## 22a. Resolved Questions
- Multiple concurrent active encryption keys with overlapping rotation window: YES (implemented via multi-key Active model + primary designation and Superseded overlap state).

## 23. Approval & Sign-off
(To be completed after review.)

---
End of Specification.
