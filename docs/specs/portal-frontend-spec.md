# Portal Frontend Technical Specification (Pilot Phase)

Version: 0.1 (Draft)  
Date: 2025-09-17  
Owner: Integration Platform Team  
Status: Draft

## 1. Purpose

Define the Angular SPA design for the EDI Trading Partner Self-Service Portal pilot focusing on credential management, file visibility, dashboard metrics, audit viewing, and production-ready authentication flow. **The frontend operates exactly as it would in production**, using standard session token authentication. Role simulation and test authentication are handled entirely by the backend - the frontend has no knowledge of "fake" vs "real" authentication modes.

## 2. Technology Stack

- Angular (Latest LTS at implementation time; target 18 if available).  
- TypeScript strict mode enabled.  
- Angular Standalone Components (no NgModules except for feature-libraries if required).  
- Angular Router with lazy-loaded feature areas.  
- State Management: Angular Signals + lightweight custom stores; fallback to NgRx only if complexity escalates.  
- UI Library: Angular Material (theming + component baseline) with custom palette meeting WCAG AA contrast.  
- Charting: ECharts (ngx-echarts) or ngx-charts (decision by bundle size spike analysis).  
- HTTP: `HttpClient` + interceptors (Error mapping, Loading indicator, FakeAuth session token attach).  
- Build: `ng build --configuration=production` with optimization + budgets.  
- Testing: Jest (unit), Playwright (E2E).  
- Linting: ESLint + Prettier.

## 3. Login Screen (Production-Ready Interface)

**Important**: The frontend implements a standard login interface that works identically in pilot and production modes. The backend handles whether authentication is real or stubbed.

- Route: `/login` (public).
- Form Fields: `Partner` (select), `User Id` (text), `Role` (select: PartnerUser | PartnerAdmin | InternalSupport).
- On submit: POST `/api/login` (or `/api/fake-login` in pilot), store returned session token in memory + `sessionStorage` (key `portalSessionToken`).
- After login: redirect to `/dashboard`.
- Token attached via `X-Session-Token` header by interceptor (standard production pattern).
- Session Expiration Handling: On 401/440-like custom response -> redirect to `/login` with toast message.
- **Frontend operates identically regardless of backend auth mode** - no special "fake" handling or banners.## 4. High-Level Feature Areas

| Feature | Route Prefix | Components (Primary) | Description |
|---------|--------------|----------------------|-------------|
| Dashboard | /dashboard | `DashboardPageComponent`, `KpiTilesComponent`, `FileCountsChartComponent`, `SuccessRatioChartComponent`, `TopErrorsTableComponent` | KPIs, charts, top errors |
| Keys | /keys | `KeysPageComponent`, `KeyListComponent`, `GenerateKeyDialog`, `UploadKeyDialog`, `RevokeKeyDialog`, `PromoteKeyButton` | PGP key lifecycle |
| SFTP | /sftp | `SftpCredentialPageComponent`, `RotatePasswordDialog` | View metadata & rotate password |
| Files | /files | `FilesPageComponent`, `FileFiltersComponent`, `FileTableComponent`, `FileDetailDrawer` | Search & drill-down |
| Audit | /audit | `AuditPageComponent`, `AuditTableComponent` | Audit event history (InternalSupport only) |
| System | /system | `VersionPageComponent`, `HealthIndicatorComponent` | Build/version info |
| Login | /login | `LoginPageComponent` | Fake role selection |

## 5. Routing Structure

```text
/ (redirect -> /dashboard if logged in)
/login
/dashboard
/keys
/sftp
/files
/files/:fileId
/audit
/system/version
```
Guards: `SessionGuard` ensures session token presence; `RoleGuard` ensures role for restricted areas (Audit requires InternalSupport). Both guards operate using standard session validation patterns.

## 6. State Management Strategy

- **AppSessionStore**: Holds session token, current user context (userId, partnerId, role) received from backend authentication.  
- **DashboardStore**: Signals for summary, time series, top errors; SSE subscription updates metrics.  
- **KeysStore**: List of keys (refresh after mutations); ephemeral private key result returned through dialog then discarded.  
- **SftpStore**: Credential metadata + last rotated.  
- **FilesStore**: Current filter criteria, paged results, selected file detail.  
- **AuditStore**: Paged audit events & filters.  
- Each store exposes: load(), refresh(), updateFilter(), dispose().  
- Caching Policy: In-memory only; invalidate on route leave > 15 min inactivity (simple timestamp check) for pilot.  

## 7. Data Models (Frontend Interfaces)

All camelCase; mirror backend DTOs.

```ts
export interface KeySummaryDto { keyId: string; fingerprint: string; algorithm: string; keySize: number; createdAt: string; validFrom: string; validTo?: string | null; status: string; isPrimary: boolean; }
export interface UploadKeyRequest { publicKeyArmored: string; validFrom?: string; validTo?: string; makePrimary?: boolean; }
export interface GenerateKeyRequest { validFrom?: string; validTo?: string; makePrimary?: boolean; }
export interface GenerateKeyResponse { privateKeyArmored: string; key: KeySummaryDto; }
export interface RevokeKeyRequest { reason?: string; }

export interface SftpCredentialMetadataDto { lastRotatedAt?: string | null; rotationMethod?: string | null; }
export interface RotatePasswordRequest { mode: 'manual' | 'auto'; newPassword?: string; }
export interface RotatePasswordResponse { password?: string; metadata: SftpCredentialMetadataDto; }

export interface DashboardSummaryDto { inboundFiles24h: number; outboundFiles24h: number; successRatePct: number; avgProcessingMs24h?: number | null; openErrors: number; totalBytes24h: number; avgFileSizeBytes24h?: number | null; connectionSuccessRate24h: number; largeFileCount24h: number; }
export interface TimeSeriesPointDto { timestamp: string; inboundCount: number; outboundCount: number; }
export interface TimeSeriesResponse { points: TimeSeriesPointDto[]; }
export interface ErrorCategoryDto { category: string; count: number; }
export interface TopErrorsResponse { categories: ErrorCategoryDto[]; }

export interface FileEventListItemDto { fileId: string; direction: string; docType: string; sizeBytes: number; receivedAt: string; processedAt?: string | null; status: string; errorCode?: string | null; }
export interface FileEventDetailDto extends FileEventListItemDto { partnerId: string; correlationId: string; errorMessage?: string | null; retryCount: number; processingLatencyMs?: number | null; }

export interface AuditEventDto { auditId: string; partnerId: string; actorUserId: string; actorRole: string; operationType: string; timestamp: string; success: boolean; metadata?: any; }

export interface Paged<T> { items: T[]; page: number; pageSize: number; totalItems: number; totalPages: number; }
export interface ErrorResponse { error: { code: string; message: string; traceId: string; }; }

// Advanced mandatory metrics
export interface ConnectionHealthPointDto { timestamp: string; success: number; failed: number; authFailed: number; successRatePct: number; }
export interface ConnectionCurrentStatusDto { partnerId: string; status: string; lastCheck: string; }
export interface ThroughputPointDto { timestamp: string; totalBytes: number; fileCount: number; avgFileSizeBytes: number; }
export interface LargeFileDto { fileName: string; sizeBytes: number; receivedAt: string; }
export interface ConnectionPerformancePointDto { timestamp: string; avgMs: number; p95Ms: number; maxMs: number; count: number; }
export interface DailyOpsPointDto { date: string; totalFiles: number; successfulFiles: number; failedFiles: number; successRatePct: number; }
export interface FailureBurstPointDto { windowStart: string; failureCount: number; }
export interface ZeroFileWindowStatusDto { windowHours: number; inboundFiles: number; flagged: boolean; }
```

## 8. Services (Frontend API Layer)

Implemented as injectable classes wrapping `HttpClient` to isolate URL paths and handle mapping.

```ts
KeyApiService {
  list(): Observable<KeySummaryDto[]>
  upload(req: UploadKeyRequest): Observable<KeySummaryDto>
  generate(req: GenerateKeyRequest): Observable<GenerateKeyResponse>
  revoke(keyId: string, req: RevokeKeyRequest): Observable<void>
  // promote(keyId: string): Observable<void> (optional future)
}

SftpApiService {
  getMetadata(): Observable<SftpCredentialMetadataDto>
  rotate(req: RotatePasswordRequest): Observable<RotatePasswordResponse>
}

DashboardApiService {
  getSummary(): Observable<DashboardSummaryDto>
  getTimeSeries(params: { from: string; to: string; }): Observable<TimeSeriesResponse>
  getTopErrors(params: { from: string; to: string; }): Observable<TopErrorsResponse>
  getConnectionHealth(params: { from: string; to: string; }): Observable<ConnectionHealthPointDto[]>
  getConnectionStatus(): Observable<ConnectionCurrentStatusDto>
  getThroughput(params: { from: string; to: string; }): Observable<ThroughputPointDto[]>
  getLargeFiles(params: { from: string; to: string; limit?: number; }): Observable<LargeFileDto[]>
  getConnectionPerformance(params: { from: string; to: string; }): Observable<ConnectionPerformancePointDto[]>
  getDailySummary(params: { days: number; }): Observable<DailyOpsPointDto[]>
  getFailureBursts(params: { lookbackMinutes: number; }): Observable<FailureBurstPointDto[]>
  getZeroFileWindow(params: { windowHours: number; }): Observable<ZeroFileWindowStatusDto>
}

FilesApiService {
  search(params: FileSearchParams): Observable<Paged<FileEventListItemDto>>
  get(fileId: string): Observable<FileEventDetailDto>
}

AuditApiService {
  search(params: AuditSearchParams): Observable<Paged<AuditEventDto>>
}

SystemApiService {
  version(): Observable<{ version: string; commit: string; buildTime: string; }>
  health(): Observable<{ status: string; }>
}
```
Supporting Param Interfaces:

```ts
export interface FileSearchParams { page?: number; pageSize?: number; direction?: string; status?: string; docType?: string; dateFrom?: string; dateTo?: string; }
export interface AuditSearchParams { page?: number; pageSize?: number; partnerId?: string; operationType?: string; dateFrom?: string; dateTo?: string; }
```

## 9. Interceptors

1. **SessionTokenInterceptor**: Adds `X-Session-Token` header if present.  
2. **ErrorMappingInterceptor**: Transforms backend `ErrorResponse` into user-friendly toast + returns typed error.  
3. **LoadingIndicatorInterceptor**: Tracks active requests via a counter signal for global progress bar.  
4. **RetryInterceptor**: Retries idempotent GETs (dashboard + files) up to 2 times on network errors (not 4xx).  

## 10. SSE Client Integration

- Service `SseClientService` establishing `EventSource` to `/api/events/stream` with session token via `X-Session-Token` header (using query param fallback `?sessionToken=` when EventSource header limitations require it).  
- Event Types -> Handlers:  
  - `file.created`: Trigger refresh of recent files (if filter active).  
  - `file.statusChanged`: Update item in FilesStore if present.  
  - `key.promoted` / `key.revoked`: Refresh KeysStore.  
  - `dashboard.metricsTick`: Patch DashboardStore summary/time-series incremental update.  
- Reconnect Strategy: Exponential backoff (1s,2s,5s,10s max 30s) preserving `Last-Event-ID`.  
- Heartbeat: Ignore comment lines starting with `:`.  
- Disable SSE gracefully if browser lacks EventSource; fallback to 60s polling using DashboardApiService + FilesApiService for delta refresh (only if route active).  
- Additional event type handling:
  - `sftp.connectionStatusChanged`: patch connection status + optionally toast if degraded.
  - `sftp.failureBurstAlert`: raise banner / indicator in dashboard header.
  - `sftp.zeroFileWindowAlert`: show warning ribbon.
  - `throughput.tick`: append/merge latest throughput point & recompute 24h aggregates.

## 11. UI/UX Components

### 11.1 Reusable Components

- `KpiTileComponent` (inputs: label, value, icon, loading).  
- `ChartCardComponent` standard layout for charts.  
- `StatusBadgeComponent` standardized color scheme for file/key statuses.  
- `PaginationControlsComponent` used by tables.  
- `ConfirmDialogComponent` for revoke/rotate confirmations.  
- `CopyToClipboardButton` for private key + generated password (immediate after generation).  
  
Advanced metrics components (mandatory, collapsible panel)


### 11.2 Dialog Flows

- Generate Key: open -> form (validFrom, validTo, makePrimary) -> submit -> show private key text area; user must click "I have copied"; closing erases from state.  
- Upload Key: ascii-armored text area validation (on paste) -> fingerprint preview (calculated client-side optional future) -> confirm.  
- Rotate Password: mode toggle (manual vs auto) -> manual password validation (sandbox regex) -> show one-time password result.  
- File Detail Drawer: shows metadata + error message if failed.  

## 12. Forms & Validation

- Use Angular Reactive Forms.  
- PGP public key basic client validation: regex start/end markers + min length threshold; deeper validation server-only.  
- Password manual complexity regex identical to backend; immediate feedback.  
- Date pickers with min/max enforcement (validFrom <= validTo).  
- Errors surfaced inline + aggregate toast for first submission failure.  

## 13. Accessibility

- All interactive elements reachable via keyboard (TAB order).  
- ARIA labels for status badges (e.g., `aria-label="Key status Active"`).  
- High-contrast theme variant toggle.  
- Chart components provide data table alternative view (toggle).  

## 14. Theming & Layout

**Note**: Detailed design specifications are provided in the companion [Portal Frontend Style Guide](./portal-frontend-style-guide.md) document, which defines the complete visual design system inspired by PointChealth.com.

### 14.1 Color Palette
- **Primary Colors**: Deep navy (#021B38) for headers and key UI elements
- **Secondary**: Blue-gray (#727B9C) for subtitles and secondary elements  
- **Accent**: Coral (#DE4843) for error states and important alerts
- **Status Colors**: Success (green), warning (orange), error (red), info (blue)
- **Neutrals**: White, light gray, medium gray, dark gray for backgrounds and text

### 14.2 Typography
- **Headings**: freight-text-pro serif font family for elegant, professional appearance
- **Body Text**: Arial/Helvetica sans-serif stack for optimal readability
- **UI Elements**: Roboto for form labels, buttons, and interface components
- **Responsive Scale**: 56px H1 down to 12px captions with appropriate line heights

### 14.3 Layout System
- **Grid**: 12-column responsive grid with Material Design breakpoints
- **Spacing**: 8px base unit scaling system (4px, 8px, 16px, 24px, 32px, etc.)
- **Containers**: Max-width 1200px with responsive padding
- **Responsive**: Grid layout adapting 3-column → 2-column → stacked

### 14.4 Component Styling
- **Cards**: White background with subtle shadows and rounded corners
- **Buttons**: Three variants (primary navy, secondary outlined, danger coral)
- **Forms**: Consistent padding, focus states, and validation styling
- **Navigation**: Clean horizontal layout with hover and active states
- **Status Badges**: Color-coded rounded badges for file/key status display

### 14.5 Accessibility Features
- **WCAG AA Compliance**: All color combinations meet 4.5:1 contrast ratio
- **Focus States**: Visible focus indicators for keyboard navigation
- **High Contrast Support**: CSS media query adaptation for accessibility needs
- **Dark Mode Ready**: CSS custom properties prepared for future dark theme  

## 15. Performance Considerations

- Route-level code splitting via lazy imports.  
- OnPush change detection strategy (or signal-driven auto-optimization).  
- Memoization of derived values (e.g., success rate calculation).  
- Avoid large bundle chart library if tree-shaking underperforms (fallback to lightweight library).  
- HTTP caching (in-memory) for static system/version call.  
- Lazy fetch advanced metrics only when user expands "Advanced Metrics" accordion; SSE updates queued until activated.  

## 16. Error Handling Patterns

- Central `ErrorToastService` uses Material snack bar.  
- Distinguish user-correctable vs system errors; show retry option.  
- SSE disconnect events show transient banner with retry progress.  

## 17. Security (Production-Ready Approach)

- **Frontend implements production-level security patterns** regardless of backend auth mode.
- Standard session token handling with secure storage practices.
- Prevent caching of sensitive dialogs (private key/password) by clearing clipboard suggestions when component destroyed.
- Sanitize displayed errorMessage from server (plain text only).
- **No special handling for pilot/fake authentication** - frontend operates as if in production.## 18. Logging & Telemetry (Optional Pilot)

- Console logging only (debug mode) for SSE connection lifecycle.  
- Optional integration stub for future App Insights JS SDK behind feature flag `enableTelemetry`.  

## 19. Testing Strategy

- Unit: Stores (business logic), Services (API layer with HttpTestingController), Utility functions (formatting).  
- Component Tests: Key list, Generate dialog, Dashboard page (async data & skeleton loaders).  
- E2E: Login -> Dashboard load; Generate key flow; Rotate password flow; File drill-down; SSE update (simulate via test backend).  
- Accessibility tests (axe-core) integrated in CI for key pages.  
- Advanced metrics tests: throughput chart renders with mock; connection health recalculates success rate; inactivity banner shown when flagged.  

## 20. Build & Deployment

- Build pipeline will compile Angular assets then copy `dist/portal` into backend `wwwroot`.  
- Environment config via `environment.ts` + `environment.prod.ts` including `apiBaseUrl` and `sseBaseUrl`.  
- Source maps disabled in production build (can enable for staging).  
- Budget thresholds: initial bundle < 350KB gzipped (excluding polyfills & Angular runtime), lazy features < 150KB each.  

## 21. Open Questions

- Should we allow partner switching without logout (multi-context testing)? (Not currently; require logout.)  
- Display key fingerprint client-side pre-upload? (Potential future via lightweight parsing.)  
- Provide CSV export for audit list? (Out of pilot scope.)  

## 22. Future Enhancements

- Replace fake login with Entra auth (Auth Code + PKCE).  
- Persist user preferences (theme, table column order) to localStorage.  
- Advanced filtering saved views for files.  
- Real-time toast for key revocation with actionable refresh.  
- Localization framework integration (i18n).  

## 23. Acceptance Criteria (Pilot)

- All defined routes navigable behind standard login.
- Key generation returns and displays private key exactly once.
- Password rotation auto mode produces length >= configured (default 24).
- Dashboard metrics load < 1.5s on seeded dataset.
- SSE updates change at least one visible KPI without full page reload.
- Audit page blocked for non-InternalSupport roles.
- All forms validated client + server with consistent error messages.
- Advanced metrics panel loads with: connection health, throughput, performance, large files (top 10), daily summary (7 days), zero file window status, and displays failure burst indicator when triggered.
- Added KPI fields (total bytes, avg file size, connection success rate, large file count) present in summary.
- **Frontend operates identically regardless of backend authentication mode**.## 24. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE unsupported in some browsers | Low | Polling fallback |
| Large chart library inflates bundle | Med | Evaluate and tree-shake; fallback library option |
| Private key lingering in memory | Med | Clear component state on destroy; avoid storing in store |
| Session token security in pilot | Low | Standard token handling patterns; backend controls auth mode |

## 25. Approval

(To be completed.)
