# Portal Frontend Style Guide

Version: 1.0  
Date: 2025-09-20  
Based on: PointChealth.com Design System Analysis  
Owner: Integration Platform Team  

## 1. Overview

This style guide defines the visual design system for the EDI Trading Partner Self-Service Portal, inspired by the professional, healthcare-focused design language of PointChealth.com. The design emphasizes trust, clarity, and accessibility while maintaining a modern, professional appearance suitable for enterprise healthcare software.

## 2. Brand Identity & Logo

### 2.1 Logo Design Principles
Based on the PointC logo design system:

- **Format**: Horizontal logo layout with icon + wordmark combination
- **Logo Elements**: 
  - Circular icon with concentric design elements (inspired by PointC's "C" symbol)
  - Company wordmark in clean, modern typography
  - Distinctive color treatment with coral accent dot
  - Consistent spacing and proportional relationships
- **Usage**: 
  - Primary logo for headers and main navigation
  - Simplified version for mobile/compact spaces
  - Monochrome version for print and special applications
  - Icon-only version for favicons and compact spaces

### 2.2 Logo Specifications
```css
.portal-logo {
  width: 150px;
  height: 42px;
  /* Maintain aspect ratio: 3.57:1 (based on PointC proportions) */
}

.portal-logo-compact {
  width: 100px;
  height: 28px;
}

.portal-logo-icon {
  width: 42px;
  height: 42px;
  /* Square icon for favicons and compact layouts */
}
```

### 2.3 Logo Color Variations
```css
/* Primary logo colors (based on PointC design) */
.logo-primary {
  --logo-icon-primary: #DE4843;    /* Coral for accent elements */
  --logo-icon-secondary: #021B38;  /* Navy for main icon shapes */
  --logo-text: #021B38;            /* Navy for wordmark */
}

/* Monochrome variations */
.logo-monochrome-dark {
  --logo-icon-primary: #021B38;
  --logo-icon-secondary: #021B38;
  --logo-text: #021B38;
}

.logo-monochrome-light {
  --logo-icon-primary: #FFFFFF;
  --logo-icon-secondary: #FFFFFF;
  --logo-text: #FFFFFF;
}
```

### 2.4 Logo File Organization

```
src/assets/logos/
├── portal-logo-primary.svg          # Primary logo (full color)
├── portal-logo-primary.png          # Primary logo (PNG fallback)
├── portal-logo-monochrome-dark.svg  # Dark monochrome version
├── portal-logo-monochrome-light.svg # Light monochrome version
├── portal-icon-primary.svg          # Icon only (full color)
├── portal-icon-monochrome.svg       # Icon only (monochrome)
└── favicon/
    ├── favicon.ico                   # 16x16, 32x32, 48x48 ICO format
    ├── favicon-16x16.png            # 16x16 PNG
    ├── favicon-32x32.png            # 32x32 PNG
    └── apple-touch-icon.png         # 180x180 Apple touch icon
```

**Logo Implementation Notes:**
- Primary logo should be implemented as SVG for scalability
- PNG fallbacks provided for older browser support
- Icon-only version extracted from the circular symbol in the PointC logo design
- All logo variations maintain the coral (#DE4843) and navy (#021B38) color scheme
- Logo files should be optimized for web delivery (< 10KB each)

## 3. Color Palette

### 3.1 Primary Colors
Based on PointChealth's sophisticated color scheme:

```css
:root {
  /* Primary Brand Colors */
  --primary-navy: #021B38;        /* Deep navy blue - primary headers, key UI elements */
  --primary-blue-gray: #727B9C;   /* Medium blue-gray - subtitles, secondary text */
  --accent-coral: #DE4843;        /* Coral accent - error states, alerts, CTAs */
  
  /* Neutral Colors */
  --white: #FFFFFF;               /* Background, cards, modals */
  --light-gray: #F8F9FA;         /* Page backgrounds, disabled states */
  --medium-gray: #6C757D;        /* Body text, descriptions */
  --dark-gray: #333333;          /* Primary text, headings */
  
  /* Status Colors */
  --success-green: #28A745;      /* Success states, completed actions */
  --warning-orange: #FFC107;     /* Warning states, pending actions */
  --error-red: #DC3545;          /* Error states, validation failures */
  --info-blue: #17A2B8;         /* Information, help text */
  
  /* Background Variants */
  --background-hero: linear-gradient(135deg, var(--primary-navy) 0%, #2C4B73 100%);
  --background-section: #FAFBFC;
  --background-card: var(--white);
}
```

### 3.2 Color Usage Guidelines

#### Primary Navy (`--primary-navy`)
- Main navigation headers
- Primary headings (H1, H2)
- Active navigation states
- Important buttons (CTAs)

#### Blue-Gray (`--primary-blue-gray`)
- Subtitle text (H5, H6)
- Secondary navigation
- Placeholder text
- Supporting labels

#### Coral Accent (`--accent-coral`)
- Error states and validation
- Important alerts
- Hover states for secondary actions
- Border highlights for form focus

#### Neutral Grays
- `--dark-gray`: Primary body text, form labels
- `--medium-gray`: Secondary text, descriptions
- `--light-gray`: Disabled states, subtle backgrounds

## 4. Typography

### 4.1 Font Stack
```css
:root {
  /* Primary font families */
  --font-heading: 'freight-text-pro', 'Georgia', 'Times New Roman', serif;
  --font-body: 'Arial', 'Helvetica Neue', 'Helvetica', sans-serif;
  --font-ui: 'Roboto', 'Arial', sans-serif;
  --font-mono: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}
```

### 4.2 Typography Scale

```css
/* Heading Styles */
.h1, h1 {
  font-family: var(--font-heading);
  font-size: 3.5rem;        /* 56px */
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--primary-navy);
  margin-bottom: 1.5rem;
}

.h2, h2 {
  font-family: var(--font-heading);
  font-size: 2.5rem;        /* 40px */
  font-weight: 600;
  line-height: 1.2;
  color: var(--primary-navy);
  margin-bottom: 1.25rem;
}

.h3, h3 {
  font-family: var(--font-heading);
  font-size: 1.875rem;      /* 30px */
  font-weight: 600;
  line-height: 1.3;
  color: var(--primary-navy);
  margin-bottom: 1rem;
}

.h4, h4 {
  font-family: var(--font-ui);
  font-size: 1.5rem;        /* 24px */
  font-weight: 600;
  line-height: 1.4;
  color: var(--primary-navy);
  margin-bottom: 0.875rem;
}

.h5, h5 {
  font-family: var(--font-ui);
  font-size: 1.125rem;      /* 18px */
  font-weight: 600;
  line-height: 1.4;
  color: var(--primary-blue-gray);
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.h6, h6 {
  font-family: var(--font-ui);
  font-size: 1rem;          /* 16px */
  font-weight: 600;
  line-height: 1.5;
  color: var(--primary-blue-gray);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Body Text */
.body-large {
  font-family: var(--font-body);
  font-size: 1.125rem;      /* 18px */
  font-weight: 400;
  line-height: 1.6;
  color: var(--medium-gray);
}

.body-regular {
  font-family: var(--font-body);
  font-size: 1rem;          /* 16px */
  font-weight: 400;
  line-height: 1.6;
  color: var(--medium-gray);
}

.body-small {
  font-family: var(--font-body);
  font-size: 0.875rem;      /* 14px */
  font-weight: 400;
  line-height: 1.5;
  color: var(--medium-gray);
}

/* UI Text */
.ui-label {
  font-family: var(--font-ui);
  font-size: 0.875rem;      /* 14px */
  font-weight: 600;
  line-height: 1.4;
  color: var(--dark-gray);
}

.ui-caption {
  font-family: var(--font-ui);
  font-size: 0.75rem;       /* 12px */
  font-weight: 400;
  line-height: 1.4;
  color: var(--primary-blue-gray);
}
```

### 4.3 Responsive Typography

```css
/* Mobile adjustments */
@media (max-width: 768px) {
  .h1, h1 { font-size: 2.5rem; }    /* 40px */
  .h2, h2 { font-size: 2rem; }      /* 32px */
  .h3, h3 { font-size: 1.5rem; }    /* 24px */
}

@media (max-width: 480px) {
  .h1, h1 { font-size: 2rem; }      /* 32px */
  .h2, h2 { font-size: 1.75rem; }   /* 28px */
  .h3, h3 { font-size: 1.375rem; }  /* 22px */
}
```

## 5. Layout & Spacing

### 5.1 Grid System
Based on 12-column responsive grid with Material Design breakpoints:

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* Breakpoints */
:root {
  --breakpoint-xs: 0;
  --breakpoint-sm: 576px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 992px;
  --breakpoint-xl: 1200px;
  --breakpoint-xxl: 1400px;
}
```

### 5.2 Spacing Scale

```css
:root {
  /* Spacing scale (8px base unit) */
  --space-xs: 0.25rem;    /* 4px */
  --space-sm: 0.5rem;     /* 8px */
  --space-md: 1rem;       /* 16px */
  --space-lg: 1.5rem;     /* 24px */
  --space-xl: 2rem;       /* 32px */
  --space-2xl: 3rem;      /* 48px */
  --space-3xl: 4rem;      /* 64px */
  --space-4xl: 6rem;      /* 96px */
}
```

### 5.3 Component Spacing

```css
/* Card spacing */
.card {
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

/* Section spacing */
.section {
  padding: var(--space-3xl) 0;
}

/* Form spacing */
.form-group {
  margin-bottom: var(--space-lg);
}

.form-input {
  padding: var(--space-md);
}
```

## 6. Component Styles

### 6.1 Buttons

```css
/* Primary Button - Main CTAs */
.btn-primary {
  background: var(--primary-navy);
  color: var(--white);
  border: 2px solid var(--primary-navy);
  padding: 0.75rem 2rem;
  font-family: var(--font-ui);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1a365d;
  border-color: #1a365d;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(2, 27, 56, 0.2);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: var(--primary-navy);
  border: 2px solid var(--primary-blue-gray);
  padding: 0.75rem 2rem;
  font-family: var(--font-ui);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--primary-blue-gray);
  color: var(--white);
  border-color: var(--primary-blue-gray);
}

/* Danger Button */
.btn-danger {
  background: var(--accent-coral);
  color: var(--white);
  border: 2px solid var(--accent-coral);
  padding: 0.75rem 2rem;
  font-family: var(--font-ui);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-danger:hover {
  background: #c73631;
  border-color: #c73631;
}
```

### 6.2 Cards & Containers

```css
.card {
  background: var(--background-card);
  border-radius: 0.5rem;
  border: 1px solid #E9ECEF;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  padding: var(--space-lg);
  transition: box-shadow 0.2s ease;
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  border-bottom: 1px solid #E9ECEF;
  padding-bottom: var(--space-md);
  margin-bottom: var(--space-lg);
}

.card-title {
  font-family: var(--font-heading);
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--primary-navy);
  margin: 0;
}
```

### 6.3 Navigation

```css
.navbar {
  background: var(--white);
  border-bottom: 1px solid #E9ECEF;
  padding: var(--space-md) 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-link {
  font-family: var(--font-ui);
  font-size: 1rem;
  font-weight: 500;
  color: var(--medium-gray);
  text-decoration: none;
  padding: var(--space-sm) var(--space-md);
  border-radius: 0.25rem;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: var(--primary-navy);
  background: var(--light-gray);
}

.nav-link.active {
  color: var(--primary-navy);
  background: var(--background-section);
  font-weight: 600;
}
```

### 6.4 Forms

```css
.form-label {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--dark-gray);
  margin-bottom: var(--space-sm);
  display: block;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  font-family: var(--font-body);
  font-size: 1rem;
  color: var(--dark-gray);
  background: var(--white);
  border: 2px solid #DEE2E6;
  border-radius: 0.375rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-blue-gray);
  box-shadow: 0 0 0 3px rgba(114, 123, 156, 0.1);
}

.form-input.error {
  border-color: var(--accent-coral);
}

.form-input.error:focus {
  box-shadow: 0 0 0 3px rgba(222, 72, 67, 0.1);
}

.form-error {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  color: var(--accent-coral);
  margin-top: var(--space-sm);
}
```

### 6.5 Status Badges

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-radius: 1rem;
}

.badge-success {
  background: rgba(40, 167, 69, 0.1);
  color: #1e7e34;
}

.badge-warning {
  background: rgba(255, 193, 7, 0.1);
  color: #b45309;
}

.badge-error {
  background: rgba(222, 72, 67, 0.1);
  color: #c73631;
}

.badge-info {
  background: rgba(23, 162, 184, 0.1);
  color: #0c5460;
}

.badge-neutral {
  background: rgba(114, 123, 156, 0.1);
  color: var(--primary-blue-gray);
}
```

## 7. Data Visualization

### 7.1 Chart Color Palette

```css
:root {
  /* Chart colors inspired by PointChealth palette */
  --chart-primary: #021B38;
  --chart-secondary: #727B9C;
  --chart-accent: #DE4843;
  --chart-success: #28A745;
  --chart-warning: #FFC107;
  --chart-info: #17A2B8;
  
  /* Extended chart palette for multi-series data */
  --chart-color-1: #021B38;
  --chart-color-2: #727B9C;
  --chart-color-3: #DE4843;
  --chart-color-4: #28A745;
  --chart-color-5: #17A2B8;
  --chart-color-6: #6F42C1;
  --chart-color-7: #FD7E14;
  --chart-color-8: #20C997;
}
```

### 7.2 Chart Container Styles

```css
.chart-container {
  background: var(--white);
  border-radius: 0.5rem;
  padding: var(--space-lg);
  border: 1px solid #E9ECEF;
  margin-bottom: var(--space-lg);
}

.chart-title {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--primary-navy);
  margin-bottom: var(--space-md);
}

.chart-legend {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  color: var(--medium-gray);
}
```

## 8. Accessibility

### 8.1 Color Contrast
All color combinations meet WCAG AA standards:
- Text on white background: 4.5:1 minimum ratio
- Large text (18pt+): 3:1 minimum ratio
- UI components: 3:1 minimum ratio

### 8.2 Focus States

```css
.focus-visible {
  outline: 2px solid var(--primary-blue-gray);
  outline-offset: 2px;
}

/* High contrast theme support */
@media (prefers-contrast: high) {
  :root {
    --primary-navy: #000000;
    --primary-blue-gray: #404040;
    --accent-coral: #CC0000;
  }
}
```

### 8.3 Dark Mode Preparation

```css
@media (prefers-color-scheme: dark) {
  :root {
    --white: #1a1a1a;
    --light-gray: #2d2d2d;
    --medium-gray: #a0a0a0;
    --dark-gray: #e0e0e0;
    --primary-navy: #4a90e2;
    --background-card: #2d2d2d;
    --background-section: #1a1a1a;
  }
}
```

## 9. Animation & Transitions

### 9.1 Standard Transitions

```css
:root {
  --transition-fast: 0.15s ease;
  --transition-normal: 0.2s ease;
  --transition-slow: 0.3s ease;
}

.transition-all {
  transition: all var(--transition-normal);
}

.transition-colors {
  transition: background-color var(--transition-normal), 
              color var(--transition-normal), 
              border-color var(--transition-normal);
}
```

### 9.2 Loading States

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.loading-skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

## 10. Implementation Guidelines

### 10.1 Angular Material Theming

```typescript
// Custom Angular Material theme
import { createTheme } from '@angular/material/core';

const customTheme = createTheme({
  palette: {
    primary: {
      main: '#021B38',
      light: '#4a5568',
      dark: '#1a202c',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#727B9C',
      light: '#a0aec0',
      dark: '#4a5568',
      contrastText: '#ffffff',
    },
    error: {
      main: '#DE4843',
      light: '#fc8181',
      dark: '#c53030',
      contrastText: '#ffffff',
    },
  },
});
```

### 10.2 CSS Custom Properties Integration

```css
/* Integration with Angular Material components */
.mat-toolbar {
  background: var(--primary-navy) !important;
  color: var(--white) !important;
}

.mat-card {
  border-radius: 0.5rem !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

.mat-button-base {
  font-family: var(--font-ui) !important;
  font-weight: 600 !important;
}
```

## 11. File Organization

```
src/styles/
├── _variables.scss          # Color, spacing, typography variables
├── _mixins.scss            # Reusable mixins and functions
├── _base.scss              # Base element styles
├── _components.scss        # Component-specific styles
├── _utilities.scss         # Utility classes
├── _themes.scss            # Theme variations (dark mode, high contrast)
└── styles.scss             # Main stylesheet importing all partials
```

## 12. Usage Examples

### 12.1 Dashboard KPI Tile
```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Files Processed Today</h3>
  </div>
  <div class="kpi-value">
    <span class="h1">1,247</span>
    <span class="badge badge-success">+12%</span>
  </div>
  <p class="body-small">Compared to yesterday</p>
</div>
```

### 12.2 Navigation Menu
```html
<nav class="navbar">
  <div class="container">
    <a href="/" class="navbar-brand">
      <img src="logo.svg" alt="Portal Logo" class="portal-logo">
    </a>
    <ul class="nav-menu">
      <li><a href="/dashboard" class="nav-link active">Dashboard</a></li>
      <li><a href="/keys" class="nav-link">Keys</a></li>
      <li><a href="/files" class="nav-link">Files</a></li>
    </ul>
  </div>
</nav>
```

### 12.3 Form Input with Validation
```html
<div class="form-group">
  <label class="form-label" for="partner-id">Partner ID</label>
  <input 
    type="text" 
    id="partner-id" 
    class="form-input error" 
    placeholder="Enter partner ID"
    aria-describedby="partner-error"
  >
  <div id="partner-error" class="form-error">
    Partner ID is required
  </div>
</div>
```

## 13. Brand Consistency Checklist

- [ ] Logo maintains proper proportions and spacing
- [ ] Primary navy used for main headings and navigation
- [ ] Blue-gray used consistently for subtitles and secondary elements
- [ ] Coral accent used sparingly for errors and alerts
- [ ] Typography hierarchy follows defined scale
- [ ] Spacing uses 8px base unit consistently
- [ ] All interactive elements have proper focus states
- [ ] Color contrast meets WCAG AA standards
- [ ] Responsive design adapts gracefully across breakpoints
- [ ] Loading states and transitions feel smooth and professional

---

*This style guide should be treated as a living document and updated as the design system evolves. All new components should reference these guidelines to maintain visual consistency across the portal.*