# Twinkle Kids — Phased Implementation Checklist

Each phase ends with passing backend checks (`pytest`, `ruff`, `mypy`), frontend checks
(`npm run check`, `npm run build`) and, from Phase 4 onward, Playwright e2e on desktop + mobile.

## Non-negotiable requirements (carry into every phase)

- [ ] Distinctive premium boutique storefront, fully responsive
- [ ] Products: images, descriptions, sizes, colours, SKUs, inventory
- [ ] Two admin-managed prices: selling price and original price/MRP
- [ ] Customer registration and login; guest checkout toggled in admin settings
- [ ] Cart and website checkout (no payment gateway)
- [ ] Separate WhatsApp ordering workflow (opening WhatsApp ≠ message sent)
- [ ] Secure admin panel
- [ ] Dynamic homepage sections and content management
- [ ] Independent product ordering per homepage section, category and collection
- [ ] Search, filters, sorting, pagination
- [ ] Customer profile and past-order history
- [ ] Admin order management and inventory management
- [ ] Configurable website settings and content
- [ ] ✗ No payment gateway · ✗ No customer order tracking page/route/timeline · ✗ No hardcoded routine content

---

## Phase 1 — Foundation ✅ (this phase)

- [x] Monorepo: `frontend/`, `backend/`, `docs/`, root README, `.gitignore`, `.gitattributes`, `.editorconfig`
- [x] FastAPI app factory, settings, versioned router, Clean Architecture layers
- [x] `/api/v1/health` (liveness) and `/api/v1/health/ready` (DB readiness, 503 on failure)
- [x] SQLAlchemy 2 engine/session, Neon-compatible URL handling, Alembic + baseline revision
- [x] pytest suite incl. architecture dependency-rule test; ruff; mypy strict
- [x] Next.js 16 shell: design tokens, fonts, header/footer, homepage placeholder, `/status`
- [x] Typed API client; Vitest + Testing Library; Playwright smoke (desktop + mobile)
- [x] `.env.example` files; docker-compose Postgres; SQLite zero-setup fallback

## Phase 1b — Neon integration ✅

- [x] Neon CLI, `neon init` (project `floral-moon-84030079`, branch `production`), `neon deploy`
- [x] Buckets `media` (public_read) and `assets` (private); env pulled to root `.env.local`
- [x] Backend loads Neon env explicitly; pooled URL for app, direct URL for Alembic
- [x] Media library: validated uploads, `media_assets` table (migration 0002), public/admin API
- [x] Live tests: Postgres CRUD, storage round-trip, API upload → reference → retrieval → delete

## Phase 2 — Domain model & database schema

- [ ] Entities + repository ports: Category, Collection, Product, ProductVariant (size, colour, SKU,
      stock), ProductImage, Price (selling, MRP; MRP ≥ selling validated in domain)
- [ ] Merchandising placements with explicit `position` per category / collection / homepage section
- [ ] User (customer/admin roles), Address, Cart, Order, OrderItem (price snapshot), internal OrderStatus
- [ ] SiteSetting (incl. guest checkout toggle, WhatsApp number), HomepageSection, ContentPage
- [ ] InventoryMovement ledger (adjustments, order reservations/deductions)
- [ ] SQLAlchemy models, repositories, Alembic migration; seed script with sample data
- [ ] Integration tests against Postgres (docker or Neon branch); money as integer minor units

## Phase 3 — Authentication & admin security

- [ ] Password hashing (argon2), JWT access + refresh in httpOnly cookies, CSRF strategy
- [ ] Role-based authorisation dependency; admin bootstrap CLI (no default admin password)
- [ ] Rate limiting on auth endpoints; audit log for admin actions
- [ ] Frontend `/admin` route group with auth guard (proxy) and login screen

## Phase 4 — Catalog API & storefront browsing

- [ ] Public catalog endpoints: list/search/filter (category, collection, size, colour, price,
      availability) / sort / paginate; product detail by slug
- [ ] Storefront pages: product listing, category, collection, product detail (gallery, size &
      colour pickers, stock state, selling price vs MRP with computed discount)
- [ ] Header navigation rendered from categories API; SEO metadata, sitemap, structured data
- [ ] Product/category/collection/banner image relations to `media_assets` (storage adapter done in 1b)

## Phase 5 — Admin catalog, CMS & site settings

- [ ] Admin CRUD: products, variants, images, prices, categories, collections
- [ ] Drag-and-drop ordering per homepage section, category and collection (independent positions)
- [ ] Homepage section builder (hero, product rails, collection tiles, banners)
- [ ] Site settings (branding text, contact, social, WhatsApp number, guest checkout) + content pages
- [ ] Replace `frontend/src/config/site.ts` fallbacks with Site Settings API data

## Phase 6 — Customer accounts

- [ ] Registration, login, logout, password reset flow
- [ ] Profile, saved addresses, past-order history (read-only list + order detail; no tracking timeline)

## Phase 7 — Cart, checkout & WhatsApp ordering

- [ ] Server-side cart (guest token + customer), stock validation, price re-check at checkout
- [ ] Website checkout → order created with "pending confirmation"-style internal status; no payment
- [ ] Guest checkout honoured only when enabled in settings
- [ ] WhatsApp flow: create a WhatsApp enquiry record + prefilled `wa.me` link; record as
      "WhatsApp opened / awaiting confirmation" — never "sent"; admin confirms manually
- [ ] Bulk-enquiry form (reference-site functionality)

## Phase 8 — Admin orders & inventory

- [ ] Order list/filters/detail, internal status transitions with history, notes
- [ ] Convert confirmed WhatsApp enquiries into orders
- [ ] Inventory dashboard: low-stock alerts, manual adjustments via the movement ledger, CSV export

## Phase 9 — Design polish & UX

- [ ] Full storefront visual design pass (poster-inspired), micro-interactions, empty/loading/error states
- [ ] Admin dashboard KPIs; accessibility audit (axe) and Lighthouse performance budget

## Phase 10 — Hardening & deployment

- [ ] CI (GitHub Actions): lint, type-check, tests, build, Playwright
- [ ] Neon production database + migration workflow; backend & frontend hosting
- [ ] Security review (headers, CORS, rate limits, dependency audit), backups, monitoring, error tracking
