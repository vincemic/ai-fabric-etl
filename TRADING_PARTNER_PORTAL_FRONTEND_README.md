# Trading Partner Portal Frontend

This is the Angular frontend for the EDI Trading Partner Self-Service Portal, built according to the specifications in the portal-frontend-spec.md.

## Project Structure

```
trading-partner-portal/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── models/
│   │   │   │   └── index.ts                 # All TypeScript interfaces
│   │   │   ├── services/
│   │   │   │   ├── auth.service.ts          # Authentication service
│   │   │   │   ├── key-api.service.ts       # PGP key API service
│   │   │   │   ├── sftp-api.service.ts      # SFTP credential API service
│   │   │   │   ├── dashboard-api.service.ts # Dashboard API service
│   │   │   │   ├── files-api.service.ts     # Files API service
│   │   │   │   ├── audit-api.service.ts     # Audit API service
│   │   │   │   ├── system-api.service.ts    # System API service
│   │   │   │   └── sse-client.service.ts    # Server-Sent Events service
│   │   │   ├── stores/
│   │   │   │   ├── app-session.store.ts     # Session state management
│   │   │   │   ├── dashboard.store.ts       # Dashboard state management
│   │   │   │   ├── keys.store.ts            # Keys state management
│   │   │   │   ├── sftp.store.ts            # SFTP state management
│   │   │   │   ├── files.store.ts           # Files state management
│   │   │   │   └── audit.store.ts           # Audit state management
│   │   │   ├── guards/
│   │   │   │   ├── session.guard.ts         # Authentication guard
│   │   │   │   └── role.guard.ts            # Role-based access guard
│   │   │   └── interceptors/
│   │   │       ├── session-token.interceptor.ts    # Adds session token to requests
│   │   │       ├── error-mapping.interceptor.ts    # Maps errors to user messages
│   │   │       ├── loading-indicator.interceptor.ts # Global loading state
│   │   │       └── retry.interceptor.ts             # Retry logic for GET requests
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   │   ├── kpi-tile.component.ts
│   │   │   │   ├── chart-card.component.ts
│   │   │   │   ├── status-badge.component.ts
│   │   │   │   ├── pagination-controls.component.ts
│   │   │   │   ├── confirm-dialog.component.ts
│   │   │   │   └── copy-to-clipboard-button.component.ts
│   │   │   ├── pipes/
│   │   │   │   └── file-size.pipe.ts
│   │   │   └── directives/
│   │   │       └── auto-focus.directive.ts
│   │   ├── features/
│   │   │   ├── login/
│   │   │   │   └── login.component.ts       # Fake login screen
│   │   │   ├── dashboard/
│   │   │   │   ├── dashboard.component.ts
│   │   │   │   ├── kpi-tiles.component.ts
│   │   │   │   ├── file-counts-chart.component.ts
│   │   │   │   ├── success-ratio-chart.component.ts
│   │   │   │   ├── top-errors-table.component.ts
│   │   │   │   └── advanced-metrics.component.ts
│   │   │   ├── keys/
│   │   │   │   ├── keys.component.ts
│   │   │   │   ├── key-list.component.ts
│   │   │   │   ├── generate-key-dialog.component.ts
│   │   │   │   ├── upload-key-dialog.component.ts
│   │   │   │   ├── revoke-key-dialog.component.ts
│   │   │   │   └── promote-key-button.component.ts
│   │   │   ├── sftp/
│   │   │   │   ├── sftp.component.ts
│   │   │   │   └── rotate-password-dialog.component.ts
│   │   │   ├── files/
│   │   │   │   ├── files.component.ts
│   │   │   │   ├── file-table.component.ts
│   │   │   │   ├── file-filters.component.ts
│   │   │   │   └── file-detail.component.ts
│   │   │   ├── audit/
│   │   │   │   ├── audit.component.ts
│   │   │   │   └── audit-table.component.ts
│   │   │   └── system/
│   │   │       └── version.component.ts
│   │   ├── app.component.ts                 # Main app component with navigation
│   │   ├── app.config.ts                    # App configuration with providers
│   │   └── app.routes.ts                    # Route definitions
│   ├── environments/
│   │   ├── environment.ts                   # Development environment
│   │   └── environment.prod.ts              # Production environment
│   ├── styles.scss                          # Global styles
│   └── main.ts                              # Bootstrap file
├── angular.json                             # Angular CLI configuration
├── package.json                             # Dependencies and scripts
├── tsconfig.json                            # TypeScript configuration
└── README.md                                # This file
```

## Installation

1. Navigate to the project directory:
   ```bash
   cd C:\tmp\ai-trading-partner-portal-frontend\trading-partner-portal
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Install additional required packages:
   ```bash
   npm install @angular/material @angular/cdk ngx-echarts echarts
   ```

## Development

1. Start the development server:
   ```bash
   ng serve
   ```

2. Navigate to `http://localhost:4200/`

3. The application will automatically reload if you change any of the source files.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Features

### Fake Authentication System
- **Route**: `/login`
- Partner selection dropdown
- User ID input
- Role selection (PartnerUser, PartnerAdmin, InternalSupport)
- Session token stored in sessionStorage
- Prominent "FAKE LOGIN MODE" banner

### Dashboard
- **Route**: `/dashboard`
- KPI tiles with loading states
- Time series charts (file counts, throughput)
- Success ratio visualization
- Top errors table
- Advanced metrics panel (collapsible)
- Real-time updates via SSE

### Key Management
- **Route**: `/keys`
- List all keys with status badges
- Generate new key pairs (shows private key once)
- Upload existing public keys
- Revoke keys with reason
- Promote/demote primary keys
- Audit trail for all operations

### SFTP Credential Management
- **Route**: `/sftp`
- View credential metadata (no password display)
- Rotate password (manual or auto-generated)
- One-time password display after rotation

### File Monitoring
- **Route**: `/files`
- Search and filter file events
- Paginated results
- File detail drill-down
- Status indicators and error messages

### Audit Trail
- **Route**: `/audit` (InternalSupport only)
- Paginated audit events
- Search and filter capabilities
- Operation type filtering

### System Information
- **Route**: `/system/version`
- Build version and commit information
- Health status indicators

## State Management

The application uses Angular Signals for state management with dedicated stores:

- **AppSessionStore**: User session and authentication state
- **DashboardStore**: Dashboard metrics and real-time updates
- **KeysStore**: PGP key lifecycle management
- **SftpStore**: SFTP credential state
- **FilesStore**: File search and detail state
- **AuditStore**: Audit trail state

## Real-time Updates

Server-Sent Events (SSE) provide real-time updates for:
- File status changes
- Key lifecycle events
- Dashboard metric updates
- Connection status changes

## HTTP Interceptors

1. **SessionTokenInterceptor**: Adds `X-Session-Token` header
2. **ErrorMappingInterceptor**: Maps API errors to user-friendly messages
3. **LoadingIndicatorInterceptor**: Global loading state management
4. **RetryInterceptor**: Automatic retry for GET requests on network errors

## Guards

- **SessionGuard**: Ensures user is authenticated
- **RoleGuard**: Enforces role-based access control

## Accessibility

- WCAG AA contrast compliance
- Keyboard navigation support
- ARIA labels for screen readers
- Alternative data table views for charts

## Environment Configuration

### Development (`environment.ts`)
```typescript
{
  production: false,
  apiBaseUrl: 'http://localhost:5000/api',
  sseBaseUrl: 'http://localhost:5000/api/events/stream',
  enableTelemetry: false,
  fakeAuthEnabled: true
}
```

### Production (`environment.prod.ts`)
```typescript
{
  production: true,
  apiBaseUrl: '/api',
  sseBaseUrl: '/api/events/stream',
  enableTelemetry: true,
  fakeAuthEnabled: false
}
```

## Backend Integration

The frontend is designed to work with the backend API at `C:\tmp\ai-trading-partner-portal-backend`.

### API Endpoints Used
- `POST /api/fake-login` - Fake authentication
- `GET /api/keys` - List keys
- `POST /api/keys/generate` - Generate key pair
- `POST /api/keys/upload` - Upload public key
- `POST /api/keys/{id}/revoke` - Revoke key
- `GET /api/sftp/credential` - Get SFTP metadata
- `POST /api/sftp/credential/rotate` - Rotate password
- `GET /api/dashboard/*` - Dashboard metrics
- `GET /api/files` - File search
- `GET /api/audit` - Audit trail
- `GET /api/events/stream` - SSE endpoint

## Testing

### Unit Tests
```bash
ng test
```

### End-to-End Tests
```bash
ng e2e
```

## Deployment

1. Build for production:
   ```bash
   ng build --configuration=production
   ```

2. Copy `dist/trading-partner-portal/*` to backend's `wwwroot/` directory

3. The backend will serve the SPA as static files

## Security Considerations

- No real authentication (pilot mode only)
- Private keys cleared from memory after display
- Session tokens stored in sessionStorage only
- Error messages sanitized
- HTTPS enforced in production

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance

- Lazy-loaded routes for code splitting
- OnPush change detection strategy
- Signal-based state management
- HTTP request caching
- Bundle size budgets enforced

## Future Enhancements

- Replace fake auth with Entra ID integration
- Add CSV export functionality
- Implement user preferences persistence
- Add localization support
- Enhanced filtering and saved views