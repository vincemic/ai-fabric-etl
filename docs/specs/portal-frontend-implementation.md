# Trading Partner Portal Frontend Technical Implementation Document

Version: 0.1 (Draft)
Date: 2025-09-20
Owner: Integration Platform Team

Related Specs:

1. EDI Trading Partner Self-Service Portal Specification
2. Portal Frontend Technical Specification (Pilot Phase)
3. Portal Frontend Style Guide

## 1. Purpose & Scope

This document provides the implementation blueprint for the Trading Partner Portal frontend (Angular SPA). It translates high-level product and frontend specifications into actionable engineering detail covering architecture, state management, API/service layer, real-time updates (SSE), security, performance, testing (Jest + Playwright), responsive design, and deployment integration. Scope focuses on Phase 1 / Pilot functionality:

- Partner self-service PGP key lifecycle (upload, generate, revoke, promote/demote implicit via primary selection logic).
- SFTP credential management (metadata view, password rotation manual or auto) and future endpoint metadata placeholder.
- File visibility & dashboard metrics (KPIs, charts, error tables, drill-down) with SSE-driven incremental updates + polling fallback.
- Audit event viewing (InternalSupport role) with pagination.
- Production-ready session token pattern decoupled from underlying identity mode (fake vs Entra future) – frontend remains agnostic.

Out-of-scope for this implementation document: backend cryptographic details, infrastructure Bicep, and deep styling token curation (see Style Guide). The document emphasizes maintainable, testable, and accessible code.

## 2. Solution Overview

The portal is a single-page Angular application served statically from the backend ASP.NET Core host. It authenticates via a session token (header `X-Session-Token`) returned by a login endpoint. Role-based route guards enforce feature visibility. Data access occurs through generated or hand-authored TypeScript service wrappers around REST endpoints defined in the backend OpenAPI (plus one SSE endpoint excluded from OpenAPI). Real-time updates leverage Server-Sent Events for push of file status changes and metric deltas; a resilient reconnect strategy ensures continuity. State is managed via lightweight signal-driven stores (no NgRx dependency initially) enforcing unidirectional data flow and clear separation of remote vs derived state.

Key engineering goals:

| Goal | Implementation Approach |
|------|-------------------------|
| Fast initial load | Route-level lazy loading + code splitting for feature areas |
| Deterministic dev data | Mock dataset seeded by backend; frontend assumes stable IDs |
| Secure handling of sensitive secrets | Ephemeral component state (private keys & generated passwords never stored centrally) |
| Real-time visibility | SSE + granular store patching (no full page reloads) |
| Accessibility | Semantic structure, ARIA labeling, keyboard navigation, contrast compliance |
| Observability | Optional lightweight console tracing; future App Insights JS hook behind flag |

## 3. Technology Stack & Tooling

| Category | Choice | Rationale |
|----------|--------|-----------|
| Framework | Angular (latest LTS) | Robust routing, forms, DI, TypeScript-first |
| Language | TypeScript (strict) | Type safety across API DTOs and stores |
| UI Library | Angular Material + custom design tokens | Accelerated baseline + brand theming |
| Charts | ECharts via ngx-echarts (tentative) | Rich chart types + theming; reevaluate bundle impact |
| State | Angular Signals custom stores | Lean vs NgRx; can migrate if complexity rises |
| HTTP | `HttpClient` + interceptors | Centralized cross-cutting concerns |
| Real-Time | Native `EventSource` (SSE) | Simplicity, server push semantics |
| Testing (unit) | Jest | Faster + isolated over Karma |
| Testing (e2e) | Playwright | Cross-browser, robust selectors, trace capability |
| Lint/Format | ESLint + Prettier | Consistency and CI enforcement |
| Code Quality | Angular ESLint rules, custom a11y checks | Guardrails |
| Type Generation (optional) | OpenAPI codegen (typescript-fetch) or handcrafted | Maintain DTO parity |

Tooling Conventions:
\n- All environment-specific base URLs injected via `environment.ts` import tokens.
- Strict null checks enforced; public APIs expose explicit nullable types.
- CI pipeline runs: lint → test (unit) → build → e2e smoke (optionally against mock backend container).

## 4. High-Level Architecture

Layers:

1. Presentation (Components + Presentational subcomponents) – purely declarative UI.
2. State Stores (Signals) – orchestrate data retrieval, local caching, derivations, SSE patching.
3. Services (API Layer) – boundary to backend; no UI logic; returns RxJS Observables converted into signals by stores.
4. Real-Time Channel – `SseClientService` distributing typed domain events to stores via a small mediator.
5. Utility & Cross-Cutting – interceptors (auth token, error mapping, loading), formatting helpers, validators.
6. Theming & Styling – global styles, design tokens, Material theme override, responsive utilities.

Data Flow:
Event (User Action or SSE) → Store method → (optional) Service call → State mutation → Component signal consumption → Change detection.

Domain Boundaries:

- Credentials Domain (PGP/SFTP) separated from Files & Dashboard domain to minimize ripple on sensitive operations.
- SSE event topic mapping ensures unrelated domains do not recompute (e.g., key events never trigger file table full reload).

Resilience Considerations:

- Idempotent GET retries via interceptor (exponential backoff minimal) for transient network issues.
- SSE reconnection strategy with Last-Event-ID to minimize missed updates.

## 5. Project Structure

```text
portal-frontend/
	src/
		app/
			core/                    # Core singleton services (Session, SseClient, ErrorToast)
			shared/                  # Reusable UI components, pipes, directives
			auth/                    # Login page + guards
			dashboard/               # Dashboard feature (summary, charts, advanced metrics)
			keys/                    # PGP key management
			sftp/                    # SFTP credential/password rotation (+ future endpoint metadata)
			files/                   # File search & detail drawer
			audit/                   # Audit history (restricted)
			system/                  # Version/health
			state/                   # Store classes (if not colocated within features)
			interceptors/            # HTTP interceptors
			models/                  # DTO interfaces (generated or manual)
			styles/                  # SCSS partials (import order: variables → mixins → base → components → utilities)
		assets/                    # Logos, icons, fonts
		environments/              # environment.ts / environment.prod.ts
	jest.config.ts
	playwright.config.ts
	tsconfig.json
	package.json
```

Co-location Option: Simpler stores can reside inside their feature folder (e.g., `dashboard/dashboard.store.ts`). Complex or cross-cutting stores remain in `state/`.

## 6. Routing & Navigation

Route Strategy:

- Root redirect to `/dashboard` when authenticated.
- Lazy loaded feature routes using dynamic imports to reduce initial bundle.
- Guards: `SessionGuard` (token presence & optional freshness ping), `RoleGuard` (role array vs route data metadata). Unauthorized route access triggers navigation to `/login` or a dedicated `403` message component.

Example Route Definition Snippet:
```ts
export const appRoutes: Routes = [
  { path: 'login', loadComponent: () => import('./auth/login-page.component').then(m => m.LoginPageComponent) },
  { path: '', canActivate: [SessionGuard], children: [
      { path: 'dashboard', loadChildren: () => import('./dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES) },
      { path: 'keys', loadChildren: () => import('./keys/keys.routes').then(m => m.KEYS_ROUTES) },
      { path: 'sftp', loadChildren: () => import('./sftp/sftp.routes').then(m => m.SFTP_ROUTES) },
      { path: 'files', loadChildren: () => import('./files/files.routes').then(m => m.FILES_ROUTES) },
      { path: 'audit', canActivate: [RoleGuard], data: { roles: ['InternalSupport'] }, loadChildren: () => import('./audit/audit.routes').then(m => m.AUDIT_ROUTES) },
      { path: 'system', loadChildren: () => import('./system/system.routes').then(m => m.SYSTEM_ROUTES) },
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' }
    ]},
  { path: '**', loadComponent: () => import('./shared/not-found.component').then(m => m.NotFoundComponent) }
];
```

Navigation Shell: A top-level `LayoutComponent` (toolbar + side nav on larger screens, collapsible drawer on tablet) wraps authenticated routes.

## 7. State Management (Signals Stores)

Pattern: Each domain store encapsulates:

- Signals: `data`, `loading`, `error`, `filters`, `pageInfo`, derived computed signals (e.g., `successRatePct` if not provided).
- Public API Methods: `load()`, `refresh()`, `updateFilters(patch)`, `dispose()`, mutation-specific actions (e.g., `generateKey(req)`).
- SSE Handling Methods: `applyEvent(evt)` invoked by mediator service.

Example Skeleton (Key Store):
```ts
@Injectable({ providedIn: 'root' })
export class KeysStore {
  readonly keys = signal<KeySummaryDto[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  constructor(private keyApi: KeyApiService) {}
  load() {
    this.loading.set(true);
    this.keyApi.list().subscribe({
      next: ks => { this.keys.set(ks); this.loading.set(false); },
      error: err => { this.error.set(err.message ?? 'Load failed'); this.loading.set(false); }
    });
  }
  patchKey(updated: KeySummaryDto) {
    const map = new Map(this.keys().map(k => [k.keyId, k] as const));
    map.set(updated.keyId, updated);
    this.keys.set([...map.values()]);
  }
  removeKey(id: string) { this.keys.set(this.keys().filter(k => k.keyId !== id)); }
}
```

Rationale for Signals:

- Fine-grained reactivity reduces unnecessary change detection.
- Simpler cognitive model than action/reducer boilerplate.
- Migration path: Wrap stores with an adapter if NgRx adoption becomes necessary.

Memory Strategy:

- Idle eviction: timestamp each store’s last consumer subscription; if > 15 minutes inactivity, allow optional `dispose()` (called by a central idle service) to release memory and require fresh load on next access.

## 8. Service Layer & API Integration

Each `*ApiService` isolates endpoint paths & DTO transformation. Keep them stateless & side-effect free (besides HTTP). Higher-level orchestration (e.g., cascading refresh after mutation) occurs in stores.

Conventions:

- Methods return `Observable<T>` – stores decide subscription termination. Consider `firstValueFrom` for one-off calls only inside async flows.
- Uniform error envelope mapping in `ErrorMappingInterceptor` converting backend JSON:API-style errors into a typed `PortalError` object.
- Pagination: Service returns `Paged<T>` as-is; store extracts and tracks `pageInfo` signal.
- Sorting and filtering passed transparently – UI only constructs query param object, no business logic duplication.

Example (Files):
```ts
search(params: FileSearchParams): Observable<Paged<FileEventListItemDto>> {
	const httpParams = new HttpParams({ fromObject: { ...serialize(params) } });
	return this.http.get<Paged<FileEventListItemDto>>(`${this.baseUrl}/files`, { params: httpParams });
}
```

OpenAPI Codegen (Optional): If adopted, a post-generation script prunes unused helpers and enforces lint rules; manual service wrappers can simply delegate to generated client functions for maintainability.

## 9. Authentication & Session Handling

Workflow:

1. User accesses `/login` and submits partner, userId, role.
2. Frontend calls `POST /api/login` (pilot) -> receives `{ token, user: { partnerId, role, userId }}`.
3. `SessionService` stores token in memory + `sessionStorage` under `portalSessionToken` (NOT localStorage to reduce persistence risk) and exposes a `session` signal.
4. `SessionTokenInterceptor` adds `X-Session-Token` header for outbound calls.
5. 401/440-like responses trigger `SessionService.clear()` and redirect with toast.
6. Logout clears token & signals.

Token Refresh: Not required in pilot (short-lived token assumed). Future: silent refresh pattern (timer-driven pre-expiry) can be added without changing component contracts.

Security Posture:

- No secret tokens written to logs or emitted in errors.
- CSP and `no-store` caching for dialogs containing sensitive output (private key/password) – enforced by parent layout applying meta tags route-aware.
- Optional inactivity timeout (e.g., 30 minutes) tracked by user interaction global listener; triggers logout banner with countdown.

## 10. Core Feature Implementations
### 10.1 PGP Key Management

Components:
- `KeysPageComponent` (list + actions toolbar)
- `GenerateKeyDialog`
- `UploadKeyDialog`
- `RevokeKeyDialog`
- `KeyDetailPanel` (optional future)

Flow (Generate):
1. User opens generate dialog → completes optional `validFrom`, `validTo`, `makePrimary`.
2. Store invokes `keyApi.generate()`; upon success:
	- Append returned key metadata to list.
	- Expose `privateKeyArmored` only inside dialog component state.
3. User must click "I have copied" to enable close; on close component wipes string (set to empty, triggers GC).
4. SSE `key.promoted` or `key.revoked` events patch store accordingly.

Flow (Upload): Validate minimal ASCII-armored structure client-side (regex for `-----BEGIN PGP PUBLIC KEY BLOCK-----`). Server authoritative for fingerprint & size.

Revocation: `RevokeKeyDialog` posts revoke endpoint; on success updates status locally without full reload or triggers store refresh logic if complex state transitions (e.g., primary revocation causing promotion) are server-driven.

Primary Key Indication: Badge + tooltip. Only one primary; when generation sets primary, previous primary visually demoted (list reactive patch).

Edge Cases:
- Overlap window: UI will show multiple Active with one Primary badge; explanatory tooltip referencing rotation window.
- PendingActivation keys visually separated (e.g., subtle clock icon) and excluded from encryption usage label.

Performance: Virtual scroll not required initial (expected small key counts). Simple list suffice.

### 10.2 SFTP Credential & Endpoint Management

Components:
- `SftpCredentialPageComponent`
- `RotatePasswordDialog`
- `EndpointMetadataPanel` (future placeholder; currently static host/port display if exposed)

Rotation Flow:
1. User opens rotate dialog → select mode manual or auto.
2. Manual mode reveals password field with live complexity check (regex + length ≥ 24 if policy).
3. Auto mode hides password field; on submit backend returns one-time password.
4. Dialog displays password with copy button + warning banner: "This password is only shown once."
5. Close dialog purges password variable.
6. Page store refreshes metadata (lastRotatedAt, rotationMethod).

Endpoint Metadata (Future): Dedicated panel may display read-only host, port, username, allowed ciphers. For now include placeholder interface + TO-DO note in code for easy enablement.

Security Considerations:
- Prevent password from entering global store or console logs.
- Clipboard copy triggers ephemeral success toast; no auto-select after copy to discourage shoulder surfing.

### 10.3 File & Dashboard Monitoring

Dashboard Components:
- `DashboardPageComponent` orchestrating child components
- `KpiTilesComponent` (flex layout adjusts per breakpoint)
- `FileCountsChartComponent` (time series)
- `SuccessRatioChartComponent` (pie/donut)
- `TopErrorsTableComponent`
- `RecentFailedFilesComponent`
- `AdvancedMetricsPanel` (collapsible; loads lazily)

File Browsing:
- `FilesPageComponent` with `FileFiltersComponent`, `FileTableComponent`, `FileDetailDrawer` (overlay for drill-down).
- Pagination controls reuse shared component.
- SSE file events update matching rows by `fileId`; if item not present and user filter matches, optionally insert at top (for recent view) or ignore if outside range.

Latency KPI: Shown as average processing time; computed server-side; fallback derived value in store if missing (sum of provided latencies / count).

Polling Fallback: If SSE disabled/unavailable, a background interval (60s) triggers partial refresh: summary, recent failed files, timeseries (since last timestamp). Interval automatically canceled when SSE active.

Error Drill-Down: Drawer shows sanitized errorMessage; large messages truncated with expandable section.

Empty & Loading States:
- Skeleton loaders for charts and tables.
- Zero-state message when no files in date range with quick action to adjust filters.

### 10.4 Audit History (InternalSupport Only)

Purpose: Provide paginated, filterable view of credential-related audit events restricted to `InternalSupport` role.

Data Characteristics:
- Typically moderate volume (bounded by credential operations) – pagination still implemented for consistency.
- Filters: `partnerId` (optional), `operationType`, date range.

Components:
- `AuditPageComponent` (feature root; owns filters + table)
- `AuditFiltersComponent` (optional extraction later)
- `AuditTableComponent`

Store (`AuditStore`) Responsibilities:
- Maintain filters & pagination state (page, pageSize, totalItems).
- Debounce filter changes (300ms) before triggering search.
- Provide derived signal `hasFilters` for enabling a Reset button.

Audit Store Skeleton:
```ts
@Injectable({ providedIn: 'root' })
export class AuditStore {
	readonly items = signal<AuditEventDto[]>([]);
	readonly loading = signal(false);
	readonly error = signal<string | null>(null);
	readonly page = signal(1);
	readonly pageSize = signal(25);
	readonly totalItems = signal(0);
	readonly filters = signal<{ partnerId?: string; operationType?: string; dateFrom?: string; dateTo?: string }>({});

	private searchSub?: Subscription;
	private readonly trigger = new Subject<void>();

	constructor(private auditApi: AuditApiService) {
		this.searchSub = this.trigger.pipe(debounceTime(300)).subscribe(() => this.load());
	}

	setFilters(patch: Partial<{ partnerId?: string; operationType?: string; dateFrom?: string; dateTo?: string }>) {
		this.filters.update(f => ({ ...f, ...patch }));
		this.page.set(1); // reset page
		this.trigger.next();
	}

	setPage(p: number) { this.page.set(p); this.trigger.next(); }
	setPageSize(sz: number) { this.pageSize.set(sz); this.page.set(1); this.trigger.next(); }

	load() {
		this.loading.set(true);
		const params: AuditSearchParams = { ...this.filters(), page: this.page(), pageSize: this.pageSize() };
		this.auditApi.search(params).subscribe({
			next: res => {
				this.items.set(res.items);
				this.totalItems.set(res.totalItems);
				this.loading.set(false);
			},
			error: err => { this.error.set(err.message ?? 'Failed to load audit events'); this.loading.set(false); }
		});
	}

	reset() { this.filters.set({}); this.page.set(1); this.trigger.next(); }
	dispose() { this.searchSub?.unsubscribe(); }
}
```

`AuditPageComponent` Skeleton:
```ts
@Component({
	selector: 'portal-audit-page',
	standalone: true,
	template: `
	<section class="page-header">
		<h2>Audit History</h2>
		<button mat-stroked-button (click)="onReset()" [disabled]="!hasFilters()">Reset Filters</button>
	</section>
	<portal-audit-filters (change)="onFilter($event)"></portal-audit-filters>
	<portal-loading *ngIf="store.loading()"></portal-loading>
	<portal-error *ngIf="store.error()" [message]="store.error()"></portal-error>
	<portal-audit-table
		*ngIf="!store.loading()"
		[events]="store.items()"
		[page]="store.page()"
		[pageSize]="store.pageSize()"
		[total]="store.totalItems()"
		(pageChange)="onPage($event)"
		(pageSizeChange)="onPageSize($event)"></portal-audit-table>
	`
})
export class AuditPageComponent implements OnInit, OnDestroy {
	readonly hasFilters = computed(() => Object.keys(this.store.filters()).length > 0);
	constructor(public store: AuditStore) {}
	ngOnInit() { this.store.load(); }
	ngOnDestroy() { this.store.dispose(); }
	onFilter(f: Partial<AuditSearchParams>) { this.store.setFilters(f); }
	onPage(p: number) { this.store.setPage(p); }
	onPageSize(sz: number) { this.store.setPageSize(sz); }
	onReset() { this.store.reset(); }
}
```

Routing Addition:
```ts
{ path: 'audit', canActivate: [RoleGuard], data: { roles: ['InternalSupport'] }, loadChildren: () => import('./audit/audit.routes').then(m => m.AUDIT_ROUTES) }
```

Accessibility & UX Notes:
- Operation type rendered with colored badge (neutral palette) + `aria-label="Operation Key Generate"`.
- Timestamp column uses `<time datetime>` element for machine readability.
- Sticky header & horizontal scroll for narrow devices.

Error Handling:
- Distinguish empty result (show informative zero-state) vs load error (retry button component).

Future Extension (Phase 2):
- CSV export button invoking backend streaming endpoint (guarded & rate-limited) once introduced.

## 11. Real-Time Updates (SSE) Integration

Endpoint: `GET /api/events/stream` (excluded from OpenAPI per spec).

Client Service (`SseClientService`):
- Accepts session token; if EventSource cannot set custom header, token appended as `?sessionToken=` query param (backend supports both).
- Configurable backoff sequence: `[1000, 2000, 5000, 10000, 15000, 30000]` ms (cap remains at 30s).
- Maintains `lastEventId` (sequence) from `event.id` field; includes `Last-Event-ID` header on reconnect when possible.
- Emits typed discriminated union events to a lightweight `EventBus` (simple `Subject` or signal-based dispatcher).

Event Parsing:
- SSE `event:` types mapped: `file.created`, `file.statusChanged`, `key.promoted`, `key.revoked`, `dashboard.metricsTick`, plus extended types (`sftp.connectionStatusChanged`, `sftp.failureBurstAlert`, `sftp.zeroFileWindowAlert`, `throughput.tick`).
- Data JSON parsed once centrally; invalid JSON triggers safe ignore + console warn (dev only). No user-facing noise.

Backpressure / Limits:
- Client debounces dashboard metric tick patches (e.g., coalesce events arriving <300ms apart) to prevent chart thrash.

Lifecycle:
1. `AppSessionStore` login success -> `SseClientService.connect()`.
2. On `EventSource` error: close & schedule reconnect unless explicit 401 close (in which case force logout).
3. On logout: call `disconnect()` (closes event source and clears state).

Fallback Polling:
- A `RealTimeFallbackService` starts only if `SseClientService` cannot establish connection after N attempts (default 5) or browser has no `EventSource` implementation; performs polling tasks (dashboard + recent failed files) every 60s with jitter (±5s) to avoid synchronized thundering herd.

Testing Hooks:
- `window.__portalTestHooks.injectSseEvent(type, payload)` in dev mode to simulate events for E2E tests without waiting for backend.

## 12. Responsive Design & Accessibility

Responsive Strategy:
- Breakpoints align with design system (xs <576, sm ≥576, md ≥768, lg ≥992, xl ≥1200).
- KPI Tiles: 4-column grid (lg), 2-column (md), single column stack (sm/xs).
- Charts: Flexible container width; maintain 16:9 aspect until width < 480px then shift to 4:3 for legibility.
- Navigation: Desktop persistent side nav (optional) or top toolbar with horizontal menu; mobile converts to hamburger-controlled drawer.
- Tables: Horizontal scroll wrapper with sticky header + sticky first column on narrow screens; alternative compact list view toggle for screens < 640px (progressive enhancement).

Accessibility (WCAG 2.1 AA):
- Semantic elements for structure (`header`, `nav`, `main`, `section`, `footer`).
- ARIA `role="status"` for real-time update region announcements (non-intrusive, only if critical events like failure burst).
- Keyboard navigation: Dialogs trap focus, ESC closes (with confirmation when sensitive data displayed not yet acknowledged).
- Color contrast enforced via palette tokens validated with automated lint step (future script).
- Focus outlines preserved; custom styles only augment not remove.
- Charts provide adjacent textual summary (toggle) enumerating key data points; accessible via screen reader.
- Form validation errors reference inputs via `aria-describedby`.

Performance vs Responsiveness:
- Avoid layout shift by reserving skeleton heights.
- Use CSS clamp for fluid typography: `clamp(1rem, 0.9rem + 0.5vw, 1.25rem)` for body text.

## 13. Theming & Styling Implementation

Sources:
- Style tokens declared in `styles/_variables.scss` mapping to CSS custom properties under `:root` + high contrast and dark mode media queries.
- Angular Material theme built from brand palette; override typography at component-level where necessary.

Structure:
- SCSS partial order: variables → mixins → functions → base → components → utilities → overrides.
- Each feature folder may include a local `.feature.scss` imported into a central `styles.scss` (avoid deep component style duplication).

Private Key / Password Dialog Styling:
- Uses monospace font section for key block with scroll container and copy button group; sets `user-select: all` convenience only when hovered button pressed.

Dark Mode Preparation:
- `prefers-color-scheme: dark` adaptation uses alternative neutrals; ensure charts adapt by injecting palette arrays responsive to current mode.

## 14. Error Handling & UX Patterns

Error Taxonomy:
- Validation (user-correctable)
- Authorization (role / token issues)
- Conflict (e.g., key fingerprint duplicate)
- System (unexpected / network)

Interceptor Mapping:
- Backend `error.code` → UI message dictionary (fallback to server message if not mapped).
- Adds `traceId` to a hidden details expander in toast for support users (role check).

Dialogs:
- Sensitive dialogs (key/private key, password) show inline alert boxes for partial failures (e.g., network retry guidance) rather than global toast to keep context.

Retry Pattern:
- Only idempotent GETs auto-retry (max 2) with exponential backoff; non-idempotent actions surface immediate error + manual retry button.

Global Error Boundary:
- A top-level `AppErrorBoundaryComponent` (wrapper) catches unrecoverable component template errors (Angular error handler) and offers reload; logs minimal info.

## 15. Security Considerations (Frontend)

Controls:
- Session token stored in `sessionStorage` only; cleared on tab close; consider future memory-only if backend supports silent re-login.
- Strict CSP meta tag: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://...` (SSE origin included). Inline allowances to be tightened by hashing once stable.
- `Referrer-Policy: no-referrer`; `X-Content-Type-Options: nosniff` provided server-side.
- Content containing secrets marked with `data-sensitive="true"` enabling a DOM mutation observer in dev to warn if moved outside dialogs.
- Clipboard use limited to explicit user action buttons; no automatic copying.

Defense-in-Depth UI Measures:
- Form input sanitization (client) but server remains authoritative.
- Prevent rendering of raw errorMessage HTML (HTML not inserted; plain text only).

## 16. Performance & Optimization

Bundle Strategies:
- Feature lazy modules; charts and advanced metrics behind dynamic imports.
- Preconnect hints for font assets if external (limit external dependencies).

Runtime Optimizations:
- Signals reduce template diff work.
- Memoize expensive derived values (e.g., aggregated time series transformations) using computed signals.
- Request collapsing: if dashboard summary + time series triggered concurrently, allow store to batch with `forkJoin` and unified loading spinner.

Code Splitting Targets:
- `dashboard-advanced` chunk only loaded when panel expanded first time; SSE events queue metrics (buffer array) until loaded (flush on import).

Performance Budget Monitoring:
- CI script reports gzipped sizes vs thresholds; failure if > defined budgets.

## 17. Testing Strategy (Jest + Playwright)

Layers:
- Unit: Pure utilities (validation, formatting), store logic (mock services), service methods (HttpTestingController).
- Component: Key dialogs, dashboard charts (mock data), file table filtering.
- Integration: Store ↔ interceptor interplay (simulate 401 triggering logout).
- E2E (Playwright): Core flows—login, generate key (copy), rotate password, view dashboard metrics update via injected SSE event, file drill-down.

Jest Config Highlights:
- Use `testEnvironment: 'jsdom'`.
- Setup file sets global mocks (e.g., EventSource stub for unit tests).

Store Unit Test Example:
```ts
describe('KeysStore', () => {
	let store: KeysStore; let api: jasmine.SpyObj<KeyApiService>;
	beforeEach(() => {
		api = jasmine.createSpyObj('KeyApiService', ['list']);
		api.list.and.returnValue(of([{ keyId: '1', fingerprint: 'abc', algorithm: 'RSA', keySize: 4096, createdAt: new Date().toISOString(), validFrom: new Date().toISOString(), status: 'Active', isPrimary: true }]));
		store = new KeysStore(api);
	});
	it('loads keys', () => {
		store.load();
		expect(store.keys().length).toBe(1);
		expect(store.loading()).toBeFalse();
	});
});
```

Playwright Directory Structure:
```
e2e/
	fixtures/
		test-users.ts
	specs/
		login.spec.ts
		key-management.spec.ts
		sftp-rotation.spec.ts
		dashboard-realtime.spec.ts
	utils/
		sse-injector.ts
```

`playwright.config.ts` Snippet:
```ts
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
	testDir: './e2e/specs',
	timeout: 30_000,
	retries: 1,
	use: {
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:4200',
		trace: 'on-first-retry',
	},
	projects: [
		{ name: 'chromium', use: { ...devices['Desktop Chrome'] } },
		{ name: 'firefox', use: { ...devices['Desktop Firefox'] } },
	]
});
```

Sample Playwright Test (Key Generation):
```ts
import { test, expect } from '@playwright/test';
test('partner admin generates key and sees private key once', async ({ page }) => {
	await page.goto('/login');
	await page.selectOption('select#role', 'PartnerAdmin');
	await page.click('button:has-text("Login")');
	await page.click('a:has-text("Keys")');
	await page.click('button:has-text("Generate Key")');
	await page.click('button:has-text("Submit")');
	const privateKey = page.locator('textarea.private-key');
	await expect(privateKey).toBeVisible();
	const keyText = await privateKey.inputValue();
	expect(keyText).toContain('BEGIN PGP PRIVATE KEY BLOCK');
	await page.click('button:has-text("I have copied")');
	await expect(privateKey).toBeHidden();
});
```

Dashboard Real-Time Test Hook Example:
```ts
test('dashboard updates via injected SSE event', async ({ page }) => {
	await page.goto('/dashboard');
	await page.evaluate(() => {
		window.__portalTestHooks.injectSseEvent('dashboard.metricsTick', { summaryDelta: { inboundFiles24h: 5 } });
	});
	await expect(page.locator('[data-kpi="inbound-files"] .kpi-value')).toContainText(/\b5\b/);
});
```

## 18. Build & Deployment Workflow

Steps (CI):
1. `npm ci`
2. Lint: `npm run lint` (ESLint + markdown lint for docs) 
3. Unit tests: `npm test`
4. Build: `ng build --configuration=production`
5. (Optional) E2E smoke against deployed test backend or local mock: `npx playwright test --project=chromium --grep @smoke`
6. Copy `dist/portal` → backend `wwwroot/` prior to publishing the combined artifact.

Environment Configuration:
- `environment.ts` (local dev): base API `http://localhost:5000/api`, SSE `http://localhost:5000/api/events/stream`.
- `environment.prod.ts`: injected via build arg tokens replaced in pipeline (e.g., `APP_API_BASE_URL`).

Cache Busting:
- Angular CLI file hashing ensures fresh assets; backend sets long cache headers except `index.html`.

Feature Flags (frontend-only initial):
- `enableAdvancedMetrics`, `enableTelemetry`, `enableDarkModePreview` loaded at bootstrap from a JSON served by backend (non-cache).

## 19. Observability & Telemetry (Optional Pilot)

Lightweight Approach:
- Console debug logs for SSE connect/disconnect controlled by `?debugSse=true` query param (dev only).
- Optional integration pathway for App Insights: lazy load script only when `enableTelemetry=true`.
- Custom events: `PortalKeyGenerateDialogOpened`, `PortalPasswordRotateCompleted` (future) emitted through an extensible telemetry adapter (no-op default).

Metrics of Interest (future JS telemetry):
- Time to Interactive, Largest Contentful Paint (LCP), SSE reconnect count per session.

## 20. Traceability Matrix (Key Requirements → Implementation)

| Requirement ID | Description (Short) | Implementation Reference |
|----------------|---------------------|--------------------------|
| FR-Key-01..03  | PGP upload & generation & storage metadata | Section 10.1 components + KeysStore + KeyApiService |
| FR-Key-04..11  | Audit, lifecycle statuses, primary logic | Section 10.1 (Edge Cases), SSE events for promote/revoke |
| FR-SFTP-01..05 | Password rotation flows & one-time display | Section 10.2 rotation flow & security considerations |
| FR-Dash-01..07 | KPIs, charts, filters | Section 10.3 Dashboard Components + Files feature |
| FR-SSE-01..08  | Real-time stream + resilience | Section 11 SSE Integration |
| FR-Audit-01..02| Audit pagination (frontend read) | Audit store/components (to be elaborated) |
| FR-API-01..03  | Consistent DTOs & pagination | Section 8 service conventions |
| NFR-Security   | HTTPS, secret handling, no private key persistence | Sections 10.1 (ephemeral), 15 security |
| NFR-Performance| p95 query targets & efficient rendering | Sections 4, 16 performance strategies |
| NFR-UX-01      | Responsive desktop/tablet | Section 12 responsive design |
| NFR-Observability | Logging/tracing hooks | Sections 11 (events), 19 telemetry |

## 21. Risks & Mitigations (Frontend Focus)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Excessive SSE event frequency spikes CPU | Medium | Debounce & batch metricsTick events |
| Private key copied to logs by accident | High | Lint rule scanning for PGP block patterns in committed code |
| Large chart lib inflates bundle | Medium | Evaluate bundle analyzer; fallback to lighter lib if > threshold |
| Memory leaks from lingering EventSource on route changes | Medium | Centralized lifecycle in `AppSessionStore` + visibility change listener |
| A11y regressions during rapid UI iteration | Medium | Automated axe tests in CI for critical pages |
| Token persistence vulnerability | High | Session-only storage, optional memory-only mode later |

## 22. Future Enhancements Readiness

Prepared Extension Points:
- SSE adapter can switch to WebSocket or Event Grid bridging by replacing a provider token.
- Feature flags infrastructure ready for progressive rollout (e.g., advanced metrics to subset of partners).
- Store abstraction allows plugging NgRx or another state lib (interfaces kept minimal).
- Endpoint metadata panel stub file ensures straightforward enablement when backend adds endpoints.

## 23. Acceptance Criteria Mapping

| Acceptance Criterion (Pilot) | Validation Approach |
|------------------------------|--------------------|
| All routes behind login | Playwright `login.spec` + route guard unit tests |
| Key generation returns private key once | Playwright key-management test + manual ephemeral state assertion |
| Password rotation complexity & one-time reveal | Playwright sftp-rotation test + unit regex tests |
| Dashboard metrics <1.5s load | Performance test (Lighthouse / custom timer) using seeded dataset |
| SSE updates KPI without reload | dashboard-realtime Playwright test with injection hook |
| Audit restricted to InternalSupport | Guard unit test + negative E2E case |
| Forms validated consistently | Unit tests for validators + visual check in E2E |
| Advanced metrics panel loads all listed datasets | Playwright advanced metrics spec (lazy import) |
| Additional KPI fields present | Unit test for DashboardSummaryDto rendering |
| Same frontend behavior real vs fake auth | Integration test substituting backend mode env var |

## 24. Glossary

- SSE: Server-Sent Events – unidirectional server-to-client streaming over HTTP.
- KPI: Key Performance Indicator tile on dashboard (e.g., inbound files 24h).
- DTO: Data Transfer Object between frontend and backend.
- Store: Encapsulated state container using Angular Signals for domain area.
- Ephemeral Secret: Sensitive value held only in component memory for a short lifespan (private key/password).
- Backoff: Increasing delay strategy between reconnection attempts.
- Idle Eviction: Clearing store data after configured inactivity window to reclaim memory.

---
End of Document (Draft)
