# Twinkle Kids — Architecture

> *Cute Styles for Little Smiles.*

Twinkle Kids is a database-driven children's clothing store: a Next.js storefront and admin UI
backed by a FastAPI service and PostgreSQL. All routine content comes from the API — products,
categories, collections, homepage sections and site settings are admin-managed, never hardcoded.

## System overview

```
 Browser ──► Next.js (frontend/)            ──►  FastAPI (backend/)  ──►  PostgreSQL
            Storefront + /admin UI                /api/v1/*                 Neon (hosted)
            Server Components fetch API          Clean Architecture        docker / SQLite (local)
```

| Concern        | Choice                                                                  |
| -------------- | ----------------------------------------------------------------------- |
| Frontend       | Next.js 16 App Router, React 19, TypeScript (strict + extra checks)     |
| Styling        | Design tokens (`src/styles/tokens.css`) + CSS Modules; Lucide icons     |
| Backend        | FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic                           |
| Database       | PostgreSQL (Neon free plan) via psycopg 3; `DATABASE_URL` only          |
| Tests          | pytest · Vitest + Testing Library · Playwright (desktop + mobile)       |
| Quality gates  | ruff (lint + format), mypy `--strict`, ESLint (next config), `tsc`      |

## Backend: Clean Architecture

```
backend/app/
  domain/            Entities, value objects, repository/port Protocols. Pure Python.
  application/       Use cases. Depend only on domain ports.
  infrastructure/    SQLAlchemy models + repositories, DB session, storage adapters.
  api/               FastAPI routers, HTTP schemas (Pydantic), dependency wiring.
  core/              Settings, version, (later) security helpers.
  main.py            App factory: create_app(settings)
```

**Dependency rule** — arrows point inward only:

```
api ──► application ──► domain ◄── infrastructure
  └──────────── wires infrastructure into ports (api/deps.py)
```

- The domain never imports FastAPI, Starlette, SQLAlchemy, Alembic or Pydantic.
- Application use cases never import FastAPI or SQLAlchemy; they receive ports.
- Infrastructure never imports FastAPI.
- `tests/unit/test_architecture.py` enforces these rules on every test run.
- Route handlers stay thin: parse input → call a use case → map the result to a response schema.

The health check is the reference vertical slice:
`HealthProbe` (domain port) → `CheckHealth` (use case) → `DatabaseHealthProbe` (infrastructure)
→ `GET /api/v1/health` and `/api/v1/health/ready` (API). New features follow the same shape.

### API conventions

- Every endpoint lives under `/api/v1`. Breaking changes go to `/api/v2`.
- OpenAPI docs are at `/docs` outside production only.
- `/health` is liveness (process up); `/health/ready` is readiness (dependencies reachable,
  returns **503** if any are down). Errors never echo connection details.

### Configuration & secrets

- `app/core/config.py` (pydantic-settings) reads environment variables / `backend/.env`.
- `DATABASE_URL` is the only DB setting. Neon URLs (`postgresql://…?sslmode=require&channel_binding=require`)
  are normalised to the psycopg 3 driver with SSL parameters preserved.
- Production refuses to start with the dev `SECRET_KEY`, a SQLite URL, or `DEBUG=true`.
- Postgres connections use `pool_pre_ping` + `pool_recycle` because Neon's free compute auto-suspends.
- Real `.env` files are git-ignored; only `.env.example` files are committed.

### Database & migrations

- One declarative `Base` with a deterministic constraint-naming convention.
- Alembic reads the same settings as the app (no URL in `alembic.ini`) and connects through
  `DATABASE_URL_UNPOOLED` (direct endpoint); the app uses the pooled `DATABASE_URL`, with psycopg
  server-side prepared statements disabled for PgBouncer. Revisions: `0001` baseline, `0002` media_assets.
- **Primary:** Neon branch `production` (linked via `.neon`, env in root `.env.local`).
  **Offline:** SQLite + in-memory storage, or Docker Postgres on host port 5433. Prefer a Neon
  dev branch (`neon checkout dev --create`) for feature work.
- Postgres is the target. Once Phase 2 introduces Postgres-specific features, integration tests will
  run against Postgres; SQLite remains only for fast unit-level tests.

### Media & object storage

Website images (product, category, collection, homepage banner, content) are stored in **Neon
Object Storage**, which Neon documents as S3-compatible; the backend uses `boto3` with SigV4 and
path-style addressing against the branch endpoint (`AWS_ENDPOINT_URL_S3`).

```
domain/      MediaAsset, ImageInfo · ports: ObjectStorage, ImageInspector, MediaAssetRepository
application/ UploadMedia · GetMedia · ListMedia · DeleteMedia · MediaUrlResolver
infrastructure/storage/  S3ObjectStorage (Neon) · InMemoryObjectStorage · PillowImageInspector
infrastructure/db/       media_assets table (metadata + bucket/key reference)
```

- Postgres is the source of truth: `media_assets` stores bucket, key, type, size, dimensions,
  SHA-256 and alt text. Catalog/CMS tables (Phase 2+) reference `media_assets.id`.
- Validation decodes the actual bytes (Pillow): JPEG/PNG/WebP/AVIF only, declared type must match,
  size and pixel limits, truncated files and decompression bombs rejected. No SVG.
- Keys are immutable (`<purpose>/<xx>/<uuid>.<ext>`) with `Cache-Control: immutable` so a CDN can
  sit in front of the public bucket later (`MEDIA_PUBLIC_BASE_URL`).
- Public assets → `media` bucket (`public_read`); private → `assets` bucket via 15-minute
  presigned URLs.
- Upload writes the object, then the row; if the row fails the object is removed. Delete removes
  the row first, then the object, so no row ever points at a missing file.
- `/health/ready` probes both Postgres and the media bucket.

## Frontend

```
frontend/src/
  app/               Routes (App Router). Server Components by default.
  components/        Reusable UI, each with a co-located CSS Module and tests.
  lib/api/           Typed API client (apiFetch, ApiError) + per-resource modules.
  config/            Static fallbacks used only until the Site Settings API exists.
  styles/tokens.css  Design tokens — colour, type, spacing, radius, shadow, motion.
```

- **Cache Components is enabled** (Next 16 default). Uncached data reads sit inside `<Suspense>`
  so pages prerender a static shell and stream data (see `app/status/page.tsx`).
- Server code calls the API via `API_BASE_URL`; browser code via `NEXT_PUBLIC_API_BASE_URL`.
- Business rules (pricing, stock, discount calculation, order validation) belong in the backend.
  The frontend renders and submits; it does not decide.
- Accessibility baseline: skip link, landmark roles, labelled icon buttons, visible focus rings,
  `prefers-reduced-motion` respected, AA-contrast token pairs, no horizontal scroll at phone width.

### Storefront (Prompt 3)

```
src/lib/catalog/      api.ts (server-only typed catalogue reads) · query.ts (URL <-> filters) · adapters.ts
src/lib/content/      getSiteContent() + types; fixtures/development-content.ts until the CMS API exists
src/lib/wishlist/     guest wishlist (product slugs in localStorage)
src/lib/bag/          bag integration point — unavailable until the server cart API ships
src/components/ui/    design system: Button, Price, Badge, Dialog/Drawer, Toast, Form controls,
                      Breadcrumbs, Skeleton/EmptyState, Motif, SectionHeading, InfoPage
src/components/{layout,home,product,catalog,search,wishlist}/
src/app/              /, /shop, /category/[slug], /collections/[slug], /products/[slug],
                      /search, /wishlist, /bag, /account, /pages/[slug]
```

- **Catalogue data is always live** (`/api/v1/products`, `/categories`). Prices are rendered from the
  API's `PriceView` (selling, MRP, discount); the browser never derives authoritative prices.
- **Editorial content is CMS-shaped** (sections with id/type/visibility/order/settings) and comes from
  a clearly labelled development fixture. It contains no products, prices, reviews or business
  claims; testimonials and contact sections stay hidden until real data is configured.
- **Cache Components:** pages are synchronous shells; `params`/`searchParams` and catalogue fetches
  are awaited inside `<Suspense>` with skeleton fallbacks. Add `"use cache"` in `lib/catalog/api.ts`
  when CDN caching is introduced.
- Products without photos render an illustrated, brand-coloured garment (`ProductArt`) — never
  placeholder stock photography.

### Storefront commerce (Prompt 5)

| Endpoint | Purpose |
| -------- | ------- |
| `GET /products/facets?category=&collection=&q=` | Size / colour / price options for a listing scope (filter panels) |
| `GET /products/{slug}/reviews` | Approved reviews only |
| `GET /collections`, `GET /content/shipping`, `GET /sitemap` | Published collections, active delivery bands, indexable slugs |
| `GET/POST/PATCH/DELETE /cart…` | Server-side bag (guest `tk_cart` HttpOnly cookie or signed-in account; merged on sign-in) |
| `POST /whatsapp-requests` | Records a WhatsApp order *request* and returns a `wa.me` link |

- **Cart:** `cart_items` stores variant + quantity only. Every response re-resolves status, stock
  and the effective variant price (`CartService` → `PricePair` / `calculate_totals`); totals and
  the delivery fee (shipping rules) are backend-calculated. `unit_price_snapshot` (migration
  `0005`) is used solely to tell shoppers a price changed since they added an item.
- **WhatsApp:** lines are validated with `OrderLineSnapshot.capture` (status, stock, price), the
  message is built from catalogue data plus the admin's message introduction, and the request is
  stored as `initiated`. No stock is reserved, nothing is marked paid or sent.
- **Frontend:** `lib/bag/` (provider + API calls), `components/bag/BagView`, `components/account/
  AccountView` (existing `/auth` endpoints), `lib/catalog/filters.ts` (facets → filter options),
  `/about` and `/contact` (CMS pages + store contact settings), `sitemap.ts` / `robots.ts`.
  In production the development fixture never supplies homepage sections.
- **Config:** `STOREFRONT_URL` (backend, links in WhatsApp messages), `NEXT_PUBLIC_SITE_URL`
  (frontend canonical / OG / sitemap), optional `MEDIA_PUBLIC_BASE_URL` for a media CDN.

## Brand direction

Palette from the poster: **navy** (`--tk-navy-*`), **warm ivory** (`--tk-ivory-*`), **blush pink**
(`--tk-blush-*`), **coral** (`--tk-coral-*`) and **soft gold** (`--tk-gold-*`). Display type is
Fraunces (soft, storybook serif); body type is Nunito Sans. `--tk-coral-600` is the coral that
passes AA on ivory for text and buttons; lighter corals are for fills and decoration only.

The reference site (fashtrendcustom.in) informs *functionality* only — product cards, collections,
filters, size/colour pickers, bulk enquiries. Its visual design, branding and imagery are not reused.

## Scope guardrails

- **No payment gateway** in this version.
- **No customer-facing order tracking** — no `/track-order`, no `/orders/[number]` tracking page,
  no tracking timeline. Customers see past orders in their profile history only.
- Internal admin order statuses are allowed for operations.
- **WhatsApp ordering:** opening WhatsApp is never treated as proof that a message was sent. The
  system records an enquiry/order *intent*; staff confirm it in the admin panel.
