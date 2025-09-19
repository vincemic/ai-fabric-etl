# Portal Backend Technical Specification (Pilot Phase)

Version: 0.1 (Draft)  
Date: 2025-09-17  
Owner: Integration Platform Team  
Status: Draft

## 1. Purpose

Define the backend technical design for the EDI Trading Partner Self-Service Portal pilot. Focus is on credential lifecycle, dashboard/file visibility, and auditability. Real authentication/authorization is intentionally deferred: a **Backend-Only Fake Login Mode** provides test authentication by injecting a selected user + role context (PartnerUser, PartnerAdmin, InternalSupport) via backend-controlled session tokens. **The frontend operates as if real authentication is in place**, making standard API calls with session tokens. This allows functional validation of the complete auth flow prior to Entra integration.

## 2. Architectural Overview

- **Runtime**: ASP.NET Core (.NET 9) single web app hosting REST API + static SPA (SPA not in scope for this doc).  
- **Pattern**: Clean / vertical slice style: Controllers -> Application Services -> Repositories -> Persistence (EF Core InMemory for pilot).  
- **State**: In-memory EF Core provider with optional JSON file persistence (feature flag `Mock:PersistToFile`).  
- **Events**: In-process domain events dispatched to SSE broadcaster.  
- **SSE**: Server-Sent Events endpoint provides near-real-time updates for file events and key lifecycle.  
- **Configuration**: `appsettings.*.json` + environment variables.  
- **Telemetry**: Serilog + (optional) Application Insights (stubbed).  
- **Packaging**: Single container image (Linux) ready for App Service.  
- **Exclusions (Pilot)**: No external storage, no real identity, no secrets management, no horizontal scale complexity.

## 3. Fake Login Mode (Backend-Only Implementation)

**Important**: Fake authentication is implemented exclusively in the backend. The frontend operates in production-like mode, sending session tokens exactly as it would with real authentication.

- Endpoint `POST /fake-login` accepts `{ "userId": string, "partnerId": string, "role": "PartnerUser"|"PartnerAdmin"|"InternalSupport" }` and returns a server-issued session token (opaque GUID) stored in in-memory session dictionary.
- Frontend sends standard `X-Session-Token: <guid>` header to establish principal (same as production).
- Backend middleware resolves principal (UserId, PartnerId, Role) from session token.
- Expiration: 8 hours idle timeout (not persisted).
- This mechanism is compiled only when `FakeAuth:Enabled=true`.
- SSE connections also send `X-Session-Token` header.
- **Frontend treats this exactly like production authentication** - it has no knowledge of "fake" vs "real" auth modes.## 4. Layered Responsibilities

- **Controllers**: HTTP concerns, model binding, pagination parsing, returning standardized error envelope.  
- **Application Services**: Orchestrate domain logic (Key generation, Password rotation, Dashboard aggregation).  
- **Domain Models**: Entities + value objects (e.g., `PgpKeyStatus`, `PasswordRotationMethod`).  
- **Repositories**: Abstractions over persistence for unit testing & future refactor.  
- **Infrastructure**: EF Core DbContext, seeders, JSON persistence adapter, SSE broadcaster, background schedulers.  
- **Common**: Result pattern, validation utilities, pagination helpers.

## 5. Data Model (Pilot Storage Schema)

Mirrors logical model from master spec; implemented via EF Core Entities.

### 5.1 Entities

```text
Partner(partnerId: Guid, name: string, status: PartnerStatus, createdAt: DateTime)
PgpKey(keyId: Guid, partnerId: Guid, publicKeyArmored: string, fingerprint: string, algorithm: string, keySize: int,
       createdAt: DateTime, validFrom: DateTime, validTo: DateTime?, revokedAt: DateTime?, status: PgpKeyStatus,
       isPrimary: bool)
SftpCredential(partnerId: Guid (PK), passwordHash: string, passwordSalt: string, lastRotatedAt: DateTime?, rotationMethod: PasswordRotationMethod?)
FileTransferEvent(fileId: Guid, partnerId: Guid, direction: FileDirection, docType: string, sizeBytes: long,
                  receivedAt: DateTime, processedAt: DateTime?, status: FileStatus, correlationId: string,
                  errorCode: string?, errorMessage: string?, retryCount: int)
AuditEvent(auditId: Guid, partnerId: Guid, actorUserId: string, actorRole: string, operationType: AuditOperationType,
           timestamp: DateTime, success: bool, metadataJson: string)
SseEventCursor(partnerId: Guid, lastSequence: long)
```

### 5.2 Enumerations

```text
PartnerStatus = Active | Suspended
PgpKeyStatus = PendingActivation | Active | Revoked | Expired | Superseded
FileDirection = Inbound | Outbound
FileStatus = Pending | Processing | Success | Failed
PasswordRotationMethod = Manual | Auto
AuditOperationType = KeyUpload | KeyGenerate | KeyRevoke | KeyDownload | SftpPasswordChange | KeyPromote | KeyDemote
```

## 6. DTO Schemas (Request/Response)

All responses use camelCase JSON. Timestamps ISO 8601 UTC. Monetary values none. Sizes in bytes.

### 6.1 Error Envelope

```json
ErrorResponse {
  error: { code: string, message: string, traceId: string }
}
```
Common codes: `VALIDATION_FAILED`, `NOT_FOUND`, `CONFLICT`, `INVALID_STATE`, `RATE_LIMITED`.

### 6.2 Pagination Envelope

```json
Paged<T> {
  items: T[],
  page: int,
  pageSize: int,
  totalItems: long,
  totalPages: int
}
```

### 6.3 Keys

```json
KeySummaryDto {
  keyId: string,
  fingerprint: string,
  algorithm: string,
  keySize: int,
  createdAt: string,
  validFrom: string,
  validTo: string|null,
  status: string,
  isPrimary: boolean
}

UploadKeyRequest { publicKeyArmored: string, validFrom: string?, validTo: string?, makePrimary: boolean? }
GenerateKeyRequest { validFrom: string?, validTo: string?, makePrimary: boolean? }
GenerateKeyResponse { privateKeyArmored: string, key: KeySummaryDto }
RevokeKeyRequest { reason: string? }
PromoteKeyRequest { } (optional Phase 1 if separate endpoint needed)
```

### 6.4 SFTP Credential

```json
SftpCredentialMetadataDto { lastRotatedAt: string|null, rotationMethod: string|null }
RotatePasswordRequest { mode: "manual"|"auto", newPassword: string? }
RotatePasswordResponse { password: string?, metadata: SftpCredentialMetadataDto }
```

### 6.5 Dashboard

```json
DashboardSummaryDto {
  inboundFiles24h: int,
  outboundFiles24h: int,
  successRatePct: number,        // 0-100 inclusive
  avgProcessingMs24h: number|null,
  openErrors: int,
  totalBytes24h: number,
  avgFileSizeBytes24h: number|null,
  connectionSuccessRate24h: number,
  largeFileCount24h: number
}

TimeSeriesPointDto { timestamp: string, inboundCount: int, outboundCount: int }
TimeSeriesResponse { points: TimeSeriesPointDto[] }

ErrorCategoryDto { category: string, count: int }
TopErrorsResponse { categories: ErrorCategoryDto[] }
```

### 6.6 Files

```json
FileEventListItemDto {
  fileId: string,
  direction: string,
  docType: string,
  sizeBytes: number,
  receivedAt: string,
  processedAt: string|null,
  status: string,
  errorCode: string|null
}

FileEventDetailDto extends FileEventListItemDto {
  partnerId: string,
  correlationId: string,
  errorMessage: string|null,
  retryCount: int,
  processingLatencyMs: number|null
}
```

### 6.7 Audit

```json
AuditEventDto {
  auditId: string,
  partnerId: string,
  actorUserId: string,
  actorRole: string,
  operationType: string,
  timestamp: string,
  success: boolean,
  metadata: object|null
}
```

### 6.8 SSE Events (data payloads only)

```json
SseEnvelope<T> { seq: number, type: string, occurredAt: string, data: T }
FileCreatedEventData { fileId: string, direction: string, docType: string }
FileStatusChangedEventData { fileId: string, oldStatus: string, newStatus: string }
KeyPromotedEventData { keyId: string, previousPrimaryKeyId: string|null }
KeyRevokedEventData { keyId: string }
DashboardMetricsTickData { summary: DashboardSummaryDto }
```

### 6.9 Advanced SFTP & Throughput Metrics (Mandatory Mock)

Mocked aggregates derived from file events + synthetic connection events.

```json
ConnectionHealthPointDto { timestamp: string, success: int, failed: int, authFailed: int, successRatePct: number }
ConnectionCurrentStatusDto { partnerId: string, status: string, lastCheck: string }
ThroughputPointDto { timestamp: string, totalBytes: number, fileCount: number, avgFileSizeBytes: number }
LargeFileDto { fileName: string, sizeBytes: number, receivedAt: string }
ConnectionPerformancePointDto { timestamp: string, avgMs: number, p95Ms: number, maxMs: number, count: int }
DailyOpsPointDto { date: string, totalFiles: int, successfulFiles: int, failedFiles: int, successRatePct: number }
FailureBurstPointDto { windowStart: string, failureCount: int }
ZeroFileWindowStatusDto { windowHours: int, inboundFiles: int, flagged: boolean }
```

DashboardSummaryDto augmentation (new fields required in pilot):

```json
{
  totalBytes24h: number,
  avgFileSizeBytes24h: number|null,
  connectionSuccessRate24h: number,
  largeFileCount24h: number
}
```

## 7. API Endpoints (Pilot Variant)

Base path `/api`. Authentication replaced by session token.

| Method | Path | Description |
|--------|------|-------------|
| POST | /fake-login | Create session token for selected role/partner |
| GET | /health | Liveness probe |
| GET | /version | Build info |
| GET | /keys | List keys (all statuses) |
| POST | /keys/upload | Upload public key |
| POST | /keys/generate | Generate key pair & return private key once |
| POST | /keys/{keyId}/revoke | Revoke key |
| GET | /sftp/credential | Fetch metadata (no password) |
| POST | /sftp/credential/rotate | Rotate password (manual or auto) |
| GET | /dashboard/summary | Summary metrics |
| GET | /dashboard/timeseries | 48h hourly counts |
| GET | /dashboard/errors/top | Top error categories |
| GET | /files | List file events (filters + pagination) |
| GET | /files/{fileId} | Detail for file |
| GET | /audit | Paginated audit events (InternalSupport only) |
| GET | /events/stream | SSE stream (not in OpenAPI) |
| GET | /dashboard/connection/health | Hourly connection outcomes (default last 24h) |
| GET | /dashboard/connection/status | Latest connection status |
| GET | /dashboard/throughput | Hourly bytes & file counts |
| GET | /dashboard/large-files | Top N large files (24h default) |
| GET | /dashboard/connection/performance | Connection timing stats |
| GET | /dashboard/daily-summary | Daily operations (7 day trend) |
| GET | /dashboard/failure-bursts | Recent failure burst windows |
| GET | /dashboard/zero-file-window | Inbound inactivity window status |
| GET | /dashboard/connection/health | Hourly connection outcomes (default last 24h) |
| GET | /dashboard/connection/status | Latest connection status |
| GET | /dashboard/throughput | Hourly bytes & file counts |
| GET | /dashboard/large-files | Top N large files (24h default) |
| GET | /dashboard/connection/performance | Connection timing stats |
| GET | /dashboard/daily-summary | Daily operations (7 day trend) |
| GET | /dashboard/failure-bursts | Recent failure burst windows |
| GET | /dashboard/zero-file-window | Inbound inactivity window status |

### 7.1 Query Parameters

- Pagination: `page` (default 1), `pageSize` (default 25, max 100)  
- Sorting (future extension): `sort=receivedAt:desc`  
- File filters: `direction`, `status`, `docType`, `dateFrom`, `dateTo` (ISO).  


### 7.2 Validation Rules (Selected)

- `publicKeyArmored`: ASCII-armored begins `-----BEGIN PGP PUBLIC KEY BLOCK-----` and ends accordingly; uniqueness of fingerprint per partner.  
- Key sizes accepted: RSA >= 2048; generation always 4096.  
- Only one `isPrimary` at a time; promoting new primary demotes previous.  
- Revoking a non-existent or already terminal state key -> `CONFLICT`.  
- Password manual mode must pass regex: `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{16,}$` (pilot can be 16 min, though auto gen uses 24).  
- Date range for files: max 90 days window.  
- `pageSize` > 100 => `VALIDATION_FAILED`.  
- Large files `limit` default 10, max 50.  
- Daily summary `days` max 14.  
- Zero-file window `windowHours` 1..12.  


## 8. Services (Application Layer)

```csharp
IKeyService
  Task<IReadOnlyList<KeySummaryDto>> ListAsync(Guid partnerId)
  Task<(GenerateKeyResponse resp, AuditEvent audit)> GenerateAsync(Guid partnerId, GenerateKeyRequest req, UserContext user)
  Task<(KeySummaryDto key, AuditEvent audit)> UploadAsync(Guid partnerId, UploadKeyRequest req, UserContext user)
  Task<AuditEvent> RevokeAsync(Guid partnerId, Guid keyId, string? reason, UserContext user)
  Task<AuditEvent> PromoteAsync(Guid partnerId, Guid keyId, UserContext user) // optional

ISftpCredentialService
  Task<SftpCredentialMetadataDto?> GetMetadataAsync(Guid partnerId)
  Task<(RotatePasswordResponse resp, AuditEvent audit)> RotateAsync(Guid partnerId, RotatePasswordRequest req, UserContext user)

IDashboardService
  Task<DashboardSummaryDto> GetSummaryAsync(Guid partnerId)
  Task<TimeSeriesResponse> GetTimeSeriesAsync(Guid partnerId, DateTime from, DateTime to)
  Task<TopErrorsResponse> GetTopErrorsAsync(Guid partnerId, DateTime from, DateTime to, int top)

IFileEventService
  Task<Paged<FileEventListItemDto>> SearchAsync(Guid partnerId, FileSearchCriteria criteria)
  Task<FileEventDetailDto?> GetAsync(Guid partnerId, Guid fileId)

IAuditService
  Task<Paged<AuditEventDto>> SearchAsync(AuditSearchCriteria criteria)

ISseEventService
  Task StreamAsync(HttpContext ctx, UserContext user, string? lastEventId)
  void PublishPartnerEvent(Guid partnerId, DomainEvent evt)

IMockDataSeeder
  Task SeedAsync()

IAdvancedMetricsService
  Task<IReadOnlyList<ConnectionHealthPointDto>> GetConnectionHealthAsync(Guid partnerId, DateTime from, DateTime to)
  Task<ConnectionCurrentStatusDto?> GetConnectionStatusAsync(Guid partnerId)
  Task<IReadOnlyList<ThroughputPointDto>> GetThroughputAsync(Guid partnerId, DateTime from, DateTime to)
  Task<IReadOnlyList<LargeFileDto>> GetLargeFilesAsync(Guid partnerId, DateTime from, DateTime to, int limit)
  Task<IReadOnlyList<ConnectionPerformancePointDto>> GetConnectionPerformanceAsync(Guid partnerId, DateTime from, DateTime to)
  Task<IReadOnlyList<DailyOpsPointDto>> GetDailyOpsAsync(Guid partnerId, int days)
  Task<IReadOnlyList<FailureBurstPointDto>> GetFailureBurstsAsync(Guid partnerId, int lookbackMinutes)
  Task<ZeroFileWindowStatusDto> GetZeroFileWindowStatusAsync(Guid partnerId, int windowHours)
```

### 8.1 Supporting Models

```csharp
UserContext { userId: string, partnerId: Guid, role: string }
FileSearchCriteria { page:int, pageSize:int, direction?:FileDirection, status?:FileStatus, docType?:string,
                     dateFrom?:DateTime, dateTo?:DateTime }
AuditSearchCriteria { page:int, pageSize:int, partnerId?:Guid, operationType?:AuditOperationType, dateFrom?:DateTime, dateTo?:DateTime }
LargeFileQuery { from:DateTime, to:DateTime, limit:int }
DailySummaryQuery { days:int }
FailureBurstQuery { lookbackMinutes:int }
ZeroFileWindowQuery { windowHours:int }
```

### 8.2 Key Generation Process

1. Validate role (must be PartnerAdmin in Fake Mode).  
2. Validate requested `validFrom`/`validTo` chronology.  
3. Generate RSA 4096 via BouncyCastle wrapper (`IAsymmetricKeyGenerator`).  
4. Compute fingerprint (SHA-1 of public key packet or modern representation).  
5. Persist new key entity with status PendingActivation or Active.  
6. If primary rules require, set new key primary & demote old (transactional).  
7. Enqueue `KeyPromoted` domain event if primary changed.  
8. Return private key armored + summary DTO.  
9. Schedule ephemeral memory wipe after serialization (finally block).  

### 8.3 Password Rotation Process

1. Validate role (PartnerAdmin).  
2. If manual, validate supplied password complexity.  
3. If auto: generate 24+ char using CSPRNG selecting char sets (upper/lower/digit/symbol) ensuring at least 4 of each category until min entropy threshold (≥ 110 bits estimated).  
4. Hash with Argon2id (libsodium or managed). Store hash + salt.  
5. Write audit event.  
6. Return plaintext only in response.  

## 9. Repositories

```csharp
IKeyRepository
  IQueryable<PgpKey> Query(Guid partnerId)
  Task<PgpKey?> FindAsync(Guid partnerId, Guid keyId)
  Task AddAsync(PgpKey key)
  Task UpdateAsync(PgpKey key)

IPartnerRepository
  Task<Partner?> FindAsync(Guid partnerId)
  IQueryable<Partner> Query()

ISftpCredentialRepository
  Task<SftpCredential?> FindAsync(Guid partnerId)
  Task UpsertAsync(SftpCredential cred)

IFileEventRepository
  IQueryable<FileTransferEvent> Query(Guid partnerId)
  Task<FileTransferEvent?> FindAsync(Guid partnerId, Guid fileId)

IAuditRepository
  IQueryable<AuditEvent> Query()
  Task AddAsync(AuditEvent evt)

ISseSequenceRepository
  long GetNextSequence(Guid partnerId)
  IReadOnlyList<SseEnvelope<object>> GetBuffered(Guid partnerId, long sinceSequence)
  void Buffer(Guid partnerId, SseEnvelope<object> evt)

IConnectionEventRepository
  IQueryable<SftpConnectionEvent> Query(Guid partnerId)
  Task AddAsync(SftpConnectionEvent evt)

// Synthetic entity
SftpConnectionEvent(eventId: Guid, partnerId: Guid, occurredAt: DateTime, outcome: ConnectionOutcome, connectionTimeMs: int)
ConnectionOutcome = Success | Failed | AuthFailed
```

## 10. SSE Implementation

- Endpoint: `GET /api/events/stream`  
- Headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`  
- Reconnect: Client sends `Last-Event-ID`; server replays buffered events (rolling 500 or 15 min).  
- Heartbeat: every 15s send `:hb\n\n`.  
- Sequence: Monotonic per partner.  
- Concurrency limit: track active connections count; if > 3 return 429 with plain text reason.  
- Buffer storage: in-memory dictionary keyed by partnerId; each value ring buffer.  
- Additional SSE event types:
  - `sftp.connectionStatusChanged`
  - `sftp.failureBurstAlert`
  - `sftp.zeroFileWindowAlert`
  - `throughput.tick`

## 11. Validation & Error Handling

- FluentValidation (or custom) for request DTOs.  
- Central exception middleware maps: `EntityNotFoundException -> 404`, `ValidationException -> 400 (VALIDATION_FAILED)`, `StateConflictException -> 409 (CONFLICT)`.  
- All errors include `traceId` using `Activity.Current.TraceId`.  

## 12. Background Jobs

- **Status Sweeper** (interval 1 min): transitions PendingActivation->Active and Active->Expired based on time.  
- **Primary Auto-Promote**: If primary expired or revoked selects most recent eligible Active.  
- **Key Overlap Manager**: Moves previous primary to Superseded and optionally revokes after overlap window (config `Keys:RotationOverlapDays`).  
- Jobs implemented via hosted services.  
- **Synthetic Metrics Generator**: Every 5 min seeds randomized connection events if sparse.  
- **Failure Burst Detector**: Evaluates rolling window; emits alert event on threshold breach.  
- **Zero File Window Monitor**: Emits alert event if inactivity window flagged.  

## 13. Configuration Keys

```text
FakeAuth:Enabled (bool)
Mock:PersistToFile (bool)
Keys:RotationOverlapDays (int, default 30)
Keys:MaxActiveOverlap (int?, optional future)
Sse:PartnerConnectionLimit (int, default 3)
Sse:BufferMin (int, default 500)
Sse:BufferTtlMinutes (int, default 15)
Password:AutoLength (int, default 24)
Password:Argon2:MemoryKb (int)
Password:Argon2:Iterations (int)
Password:Argon2:DegreeOfParallelism (int)
Metrics:FailureBurstWindowMinutes (int, default 15)
Metrics:FailureBurstThreshold (int, default 5)
Metrics:ZeroFileWindowHours (int, default 2)
Metrics:LargeFileDefaultLimit (int, default 10)
Metrics:LargeFileMaxLimit (int, default 50)
Metrics:DailySummaryMaxDays (int, default 14)
Metrics:SyntheticConnectionSeed (bool, default true)
```

## 14. Non-Functional (Pilot Expectations)

- p95 Key generation request < 1s (excluding first JIT).  
- File list pagination query (500 dataset) < 150ms p95.  
- Memory footprint < 300MB baseline.  
- Code quality: analyzers warnings = 0.  
- Logging: structured JSON, no secrets, no private key material.  
- Advanced metrics endpoints p95 < 750ms with 10k file + 2k connection events dataset.  

## 15. Testing Strategy

- Unit: Services (key, password, dashboard).  
- Integration: Repository operations (in-memory context).  
- Contract: OpenAPI snapshot test.  
- SSE: Simulated event publication & replay test for Last-Event-ID.  
- Security placeholder: Ensure endpoints reject missing session token when FakeAuth enabled.  

## 16. OpenAPI Conventions

- OpenAPI 3.1 generated via Swashbuckle; exclude `/fake-login` optionally (flag) and always exclude `/events/stream`.  
- Tags: Keys, Sftp, Dashboard, Files, Audit, System.  
- Components: `ErrorResponse`, `PagedOfFileEventListItemDto` etc.  

## 17. Deployment (Pilot Simplified)

- Container build multi-stage: restore -> build -> publish -> copy `wwwroot` placeholder.  
- Environment variable toggles FakeAuth.  

## 18. Future (Post-Pilot) Hooks

- Replace FakeAuth with Entra integration middleware.  
- Swap in persistent storage (PostgreSQL / Azure SQL).  
- External event bus (Redis / Event Grid) for SSE scale-out.  
- Secrets to Key Vault (Argon2 parameters, signing keys).  
- Replace synthetic metrics with real SFTP ingestion collector.  

## 19. Out of Scope (Backend Pilot)

- Multi-tenant data isolation beyond partnerId filtering.  
- Large dataset performance tuning.  
- External notifications.  

## 20. Risks

| Risk | Mitigation |
|------|------------|
| Missing replay events on restart | Document limitation; persistence later |
| FakeAuth accidentally deployed to prod | Build guard + config assertion on startup |
| Argon2 parameters too weak | Provide config + benchmark guidance |

## 21. Approval

(To be completed.)
