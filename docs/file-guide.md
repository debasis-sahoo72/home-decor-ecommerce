# Repository file guide

## Additions and changes in phases 03–06

| File | Purpose |
| --- | --- |
| `frontend/src/app/tokens.css` | Tailwind v4 semantic colors, typography, spacing, breakpoints, radii, shadows and primitive styles |
| `frontend/scripts/check-contrast.mjs` | Checks intended token color pairs against text/control contrast targets |
| `docs/design-system.md` | Complete component/state/accessibility specification without complete pages |
| `docs/database.md` | Relationships, ER diagram, integrity rules, audit states and seed strategy |
| `docs/authentication.md` | Backend architecture, auth protocol, configuration and launch limitations |
| `backend/app/models/__init__.py` | Registers mapped entities for Alembic |
| `backend/app/models/entities.py` | Twenty PostgreSQL tables, ORM relationships and constraints |
| `backend/alembic/versions/0001_initial.py` | Frozen initial schema, timestamp/audit triggers and immutable order snapshots |
| `backend/app/api/__init__.py` | API package marker |
| `backend/app/api/auth.py` | Versioned authentication endpoints and cookie transport |
| `backend/app/api/health.py` | Liveness/readiness router |
| `backend/app/api/dependencies.py` | Reusable identity, administrator, origin and CSRF checks |
| `backend/app/core/__init__.py` | Shared infrastructure package marker |
| `backend/app/core/errors.py` | Safe application error type |
| `backend/app/core/security.py` | Argon2id hashing, opaque token digests and signed pre-auth tokens |
| `backend/app/schemas/__init__.py` | Schema package marker |
| `backend/app/schemas/auth.py` | Validated credentials/registration and explicit public response types |
| `backend/app/services/__init__.py` | Service package marker |
| `backend/app/services/auth.py` | Registration/login, persistent throttling, sessions and revocation |
| `backend/app/cli.py` | Hidden-input admin creation and expired-auth cleanup commands |
| `backend/app/seed.py` | Idempotent category-only reference seeds |
| `backend/tests/conftest.py` | Real PostgreSQL migration fixture and per-test rollback isolation |
| `backend/tests/test_auth.py` | Authentication, authorization and abuse-control regressions |
| `backend/tests/test_database.py` | Money/stock/foreign-key constraints, audit transitions and snapshot integrity |
| `backend/tests/test_config.py` | Secure production settings and cookie checks |

Existing `main.py` is now an application factory with safe errors, request logging, bounded bodies and restricted CORS; `config.py` adds auth settings; `db.py` adds naming conventions/request-scoped injection; health tests use the new factory state. Alembic supports supplied test connections. CI now runs real PostgreSQL authentication tests, contrast checks and a migration round trip. Lockfiles/environment examples and the README are updated. `globals.css` imports tokens and respects reduced motion. Local `.tools/postgres`, `.tools/pgdata`, `.tools/pg-password`, `.tools/postgres.zip` and `.tools/postgres.log` are ignored development artifacts, never source or production credentials.

The sections below describe the original phase-02 file responsibilities; empty-schema/setup-only statements in them are historical and superseded above.

Every authored or committed file is listed below. Dependency trees, caches and virtualenv contents are generated third-party files and are described as groups rather than individually.

## Root and automation

| File | Purpose |
| --- | --- |
| `README.md` | Prerequisites, exact setup/run/health commands, manual tasks and Git publishing instructions |
| `.gitignore` | Excludes secrets, dependencies, caches, local tooling and build output; keeps environment examples |
| `.gitattributes` | Normalizes text to LF and marks common image formats binary |
| `.editorconfig` | Shared indentation, encoding and whitespace conventions |
| `.env.example` | Development database variables consumed by Compose |
| `compose.yaml` | Optional loopback-only PostgreSQL 17 container, persistent volume and readiness probe |
| `.github/workflows/ci.yml` | Frontend lint/types/build; backend lint/tests plus real PostgreSQL migration/readiness checks on GitHub |

## Documentation

| File | Purpose |
| --- | --- |
| `docs/architecture.md` | Complete phase 01 design, future behavior, assumptions, risks and primary references |
| `docs/file-guide.md` | This per-file explanation |
| `docs/verification.md` | Recorded verification results and remaining environment constraints |

## Frontend

| File | Purpose |
| --- | --- |
| `frontend/package.json` | Exact direct dependencies, Node version requirement and development/check/build commands |
| `frontend/package-lock.json` | npm-resolved dependency tree used by reproducible `npm ci` installs |
| `frontend/.env.example` | Server-only FastAPI URL; no browser-exposed secret |
| `frontend/next.config.ts` | Same-origin `/api/*` rewrite to FastAPI |
| `frontend/tsconfig.json` | Strict TypeScript and Next.js type integration, plus `@/*` source alias |
| `frontend/next-env.d.ts` | Next.js-maintained ambient type references |
| `frontend/postcss.config.mjs` | Tailwind v4 PostCSS plugin; v4 does not need a legacy Tailwind config file |
| `frontend/eslint.config.mjs` | Next.js Core Web Vitals and TypeScript lint rules, with generated output excluded |
| `frontend/src/app/layout.tsx` | Root HTML, global stylesheet and development-only noindex metadata |
| `frontend/src/app/globals.css` | Tailwind import and minimal system-font baseline |
| `frontend/src/app/page.tsx` | Static development landing page with API health link, not a commerce homepage |

## Backend

| File | Purpose |
| --- | --- |
| `backend/pyproject.toml` | Python package/build metadata, direct dependency ranges, optional development dependencies and tool settings |
| `backend/requirements.lock` | Exact runtime/development/build dependency versions, with Windows-only markers where needed |
| `backend/.env.example` | Typed application environment and local PostgreSQL URL |
| `backend/app/__init__.py` | Identifies the application package |
| `backend/app/config.py` | Cached typed settings loaded from process environment or the backend `.env` |
| `backend/app/db.py` | SQLAlchemy declarative base, connection pool and request-scoped session dependency |
| `backend/app/main.py` | FastAPI app, development docs, liveness and database readiness routes |
| `backend/alembic.ini` | Alembic paths, without embedded database credentials |
| `backend/alembic/env.py` | Online/offline migration environment using application settings and model metadata |
| `backend/alembic/script.py.mako` | Template for future migration revisions |
| `backend/alembic/versions/.gitkeep` | Preserves the empty revisions directory until the database-design phase |
| `backend/tests/test_health.py` | Verifies liveness does not touch the DB, readiness issues a query, and DB failures return a safe 503 |

## Local generated files (ignored)

| Path | Purpose |
| --- | --- |
| `.git/` | Existing repository metadata; local branch and line-ending settings were configured |
| `.env`, `backend/.env`, `frontend/.env.local` | Working copies of example settings, never committed |
| `.tools/npm/` | npm extracted locally because this host's bundled Node does not include npm; standard installations do not need it |
| `frontend/node_modules/` | Installed npm packages |
| `frontend/.next/`, `frontend/*.tsbuildinfo` | Next.js and TypeScript generated artifacts |
| `backend/.venv/` | Isolated Python interpreter and installed dependencies |
| `backend/*.egg-info/` | Metadata generated by installing the backend editable package |
| `**/__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Python bytecode and test/lint caches |

The database schema intentionally contains no business tables or seed data. Docker-managed PostgreSQL data, if created, lives in its named volume rather than this repository.
