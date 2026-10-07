# Keeply — Project Overview

> Read-later / bookmark manager. Save links or notes, organize them in user-scoped categories, extract article content asynchronously, and manage lifecycle (to-do → completed → auto-purge).

---

## 1. Tech Stack

### Backend (`backend/`)
| Layer | Technology |
|-------|------------|
| Framework | **Django 6.1.1** |
| API | **Django REST Framework 3.18.1** + **django-filter 24.x** |
| Auth | **djangorestframework-simplejwt 5.5.1** (Access 15 min / Refresh 7 days, rotation + blacklist via `token_blacklist`) |
| DB | **PostgreSQL** via **psycopg 3.3.5** (SQLite fallback in dev) |
| Async | **Celery 5.6.3** + **django-celery-beat** + **Redis** (broker + result backend) |
| Env | **django-environ 0.14.0** (`.env.base` + `.env.production`) |
| Static (prod) | **WhiteNoise** `CompressedManifestStaticFilesStorage` |
| Python | `.venv` in-repo, `asgiref 3.12` (WSGI + ASGI configured) |

### Frontend (`frontend/`)
| Layer | Technology |
|-------|------------|
| App framework | **Expo SDK ~57** + **React Native 0.86.3** + **React 19.2.3** |
| Routing | **Expo Router ~57** (file-based, routes live in `src/app/`) |
| Language | **TypeScript ~6.0** |
| HTTP | **axios 1.20** |
| Secure storage | **expo-secure-store ~57** (JWT tokens) |
| UI | `expo-font` (Inter), `expo-linear-gradient`, `expo-image`, `react-native-reanimated 4.5`, `react-native-gesture-handler`, `react-native-safe-area-context` |
| Build | EAS Build / `expo-doctor` / Continuous Native Generation (no checked-in `ios/`/`android/`) |

### Infra / Tooling
- Settings split: `config/settings/{base,development,production,test}.py`
- Git branch `master`, `.gitignore` covers `.env*`, `.venv`, `db.sqlite3`, `node_modules`
- `frontend/AGENTS.md` — **mandatory Expo rules**: always check SDK major version, use `npx expo install`, run `npx tsc --noEmit` + `npx expo lint` + `npx expo-doctor` before done.

---

## 2. Project Purpose

**Keeply** is a personal read-later service:

1. **Save anything** — a `SavedItem` requires `name` *or* `url` (DB check constraint). Optional `url` triggers an async extraction pipeline.
2. **Organize** — user-scoped `Category` (`name` unique per user) linked to items through `SavedItemCategory` with a `priority` (≥ 1). Bulk-replaced on update.
3. **Extract** — Celery task fetches the URL, validates content-type/size, parses `body_text` + `metadata` (title, description, og tags, etc.) — failures are recorded, never crash the flow.
4. **Track status** — `status: to_do | completed` (with `completed_at` consistency constraint) + `extraction_status: pending | processing | done | failed | no_url`.
5. **Lifecycle** — `CustomUser` has `plan` (`FR`/`PR`), `premium_until`, and `completed_items_retention_days` (default 7). Two daily Beat jobs expire premium and purge old `completed` items.
6. **Mobile client** — Expo app with JWT auth, token refresh, and filtered/searchable/ordered item lists.

---

## 3. Architecture

```
keeply/
├── backend/
│   ├── config/               # Django project
│   │   ├── settings/
│   │   │   ├── base.py       # INSTALLED_APPS, MIDDLEWARE, DRF/JWT/Celery/Beat, AUTH_USER_MODEL
│   │   │   ├── development.py
│   │   │   ├── production.py # HSTS, WhiteNoise, SECURE_PROXY_SSL_HEADER, logging
│   │   │   └── test.py
│   │   ├── urls.py           # /admin/ + /api/v1/auth/ + /api/v1/
│   │   ├── wsgi.py / asgi.py
│   │   └── celery.py         # Celery("keeply"), autodiscover_tasks
│   ├── apps/
│   │   ├── users/            # CustomUser, Register/Profile/ChangePassword/Logout views
│   │   ├── saved_items/      # Category / SavedItem / SavedItemCategory + extraction/
│   │   │   └── extraction/   # fetcher.py, parser.py, pipeline.py, security.py
│   │   └── core/             # pagination.StandardPagination (20 / max 100)
│   ├── tests/
│   └── manage.py / requirements.txt / .venv/
└── frontend/
    ├── src/
    │   ├── app/              # Expo Router routes: _layout.tsx, index.tsx, login.tsx, explore.tsx
    │   ├── components/       # ui/{Card,Button,TextInput}, app-tabs, themed-*, add-item-modal, item-detail-modal
    │   ├── api/              # client.js (axios + SecureStore interceptor), auth.js, savedItems.js
    │   ├── context/AuthContext.tsx
    │   ├── hooks/            # use-color-scheme, use-theme
    │   └── constants/theme.ts + global.css
    ├── app.json              # Expo config (router, splash, secure-store plugin)
    ├── package.json
    └── AGENTS.md             # Expo contribution rules
```

### Data Model

**`users.CustomUser`** (email = `USERNAME_FIELD`, `first_name` required)
```
CustomUser
  email (unique), first_name, last_name?
  plan: FR | PR, premium_until?, completed_items_retention_days=7
  full_name @property, ordering: first_name, last_name, email
```

**`saved_items.Category`**
```
Category
  user FK -> CustomUser (CASCADE, related_name=categories)
  name (50), color (9, default #3299a8)
  UniqueConstraint(user, name), ordering(name)
  QuerySet.visible_to(user)
```

**`saved_items.SavedItem`**
```
SavedItem
  user FK -> CustomUser, categories M2M through SavedItemCategory
  name? (255), url? (500), source (50, derived from URL)
  extracted_content JSON?, metadata JSON?, extraction_status, extraction_error?, extraction_version UUID
  status: to_do | completed, completed_at?, created_at, updated_at
  Constraints: name_or_url_required, status/completed_at consistent
  ordering: -created_at, -completed_at, name
  QuerySet.visible_to(user)
```

**`saved_items.SavedItemCategory`** (through table)
```
SavedItemCategory
  saved_item FK, category FK, priority ≥1 (default 1)
  UniqueConstraint(saved_item, category)
```

### API

**Base:** `config/urls.py`
```
admin/              -> django admin
api/v1/auth/        -> apps.users.urls
api/v1/             -> apps.saved_items.urls
```

**Auth (`apps.users.urls`)**
| Method | Path | View | Auth |
|--------|------|------|------|
| POST | `api/v1/auth/register/` | `RegisterView` | AllowAny — returns `{user, refresh, access}` |
| POST | `api/v1/auth/token/` | `TokenObtainPairView` | AllowAny |
| POST | `api/v1/auth/token/refresh/` | `TokenRefreshView` | AllowAny |
| GET/PUT/PATCH | `api/v1/auth/me/` | `ProfileView` | IsAuthenticated |
| PUT | `api/v1/auth/me/change-password/` | `ChangePasswordView` | IsAuthenticated |
| POST | `api/v1/auth/logout/` | `LogoutView` | IsAuthenticated — blacklists refresh token |

**Saved Items (`apps.saved_items.urls` — DefaultRouter)**
| ViewSet | Prefix | Filters |
|---------|--------|---------|
| `CategoryViewSet` | `api/v1/categories/` | `visible_to(user)` |
| `SavedItemViewSet` | `api/v1/saved-items/` | `DjangoFilterBackend` (`SavedItemFilter`) + `SearchFilter(name,url,source)` + `OrderingFilter(created_at,completed_at,name)` default `-created_at` |

DRF defaults (`base.py`): `JWTAuthentication`, `IsAuthenticated`, `StandardPagination` (page 20, `page_size` query param, max 100).

**Serializers**
- `CategorySerializer`: `HiddenField(user=CurrentUserDefault)` + `UniqueTogetherValidator(user, name)`.
- `SavedItemSerializer`: nested `SavedItemCategorySerializer(category, priority)` via `category_links`; validates `name or url`, rejects duplicate categories, validates category ownership; delegates `create`/`update` to `services.py`; `extracted_content/metadata/source/completed_at/extraction_*` are read-only.

### Async / Extraction

**Services (`saved_items/services.py`)** — transactional, called by serializers:
- `create_saved_item`: derive `source`, set `completed_at` if `completed`, set `extraction_status=NO_URL` if no url else `PENDING`; `_sync_categories` (delete + bulk_create); `_queue_extraction` via `transaction.on_commit` → `extract_content_task.delay(id, version)`.
- `update_saved_item`: handle `status` transition, `url` change (new `extraction_version` UUID, reset content/metadata/error, recompute `source`), resync categories if provided.

**Pipeline (`extraction/pipeline.py` → `fetcher.py` + `parser.py` + `security.py`)**
```
run_extraction(id, expected_version)
  ├─ stale check: extraction_version mismatch → skip
  ├─ no url → mark NO_URL
  ├─ mark PROCESSING
  ├─ fetch_url(url) → FetchError → mark FAILED
  └─ parse_fetch_result → mark DONE (metadata + body_text) or FAILED
```
All state transitions are guarded by `filter(pk, extraction_version)` to avoid racing stale tasks.

**Celery Tasks (`saved_items/tasks.py`, `users/tasks.py`)**
- `extract_content_task(id, version)` — `autoretry_for=(Exception,)` 3 retries, exponential backoff max 300s + jitter.
- `purge_expired_completed_items` — groups by distinct `completed_items_retention_days`, deletes `completed` items where `completed_at <= now - retention_days`.
- `expire_premium_users` — (users app).

**Beat Schedule (`base.py`)**
```
expire-premium-users-daily      00:00  apps.users.tasks.expire_premium_users
purge-expired-completed-items   00:30  apps.saved_items.tasks.purge_expired_completed_items
```

### Frontend Architecture

**Router (`src/app/_layout.tsx`)** — `ThemeProvider` + `AuthProvider` + `AnimatedSplashOverlay` → `RootContent` gates `AppTabs` (authenticated) vs `LoginScreen`. Uses `Inter` fonts, `SplashScreen.preventAutoHide`.

**Auth (`src/context/AuthContext.tsx` + `src/api/client.js` + `src/api/auth.js`)**
- `AuthContext` holds `isAuthenticated / isLoading` via `SecureStore.getItem('access_token')`; `login/register/logout` delegate to `api/auth.js`.
- `api/client.js` axios instance `BASE_URL=http://10.187.251.107:8000/api/v1` — request interceptor injects `Bearer access_token`; response interceptor on 401 (non-`/auth/` requests) single-flights `refreshAccessToken()` (`POST /auth/token/refresh/` with stored refresh) then retries; on refresh failure clears tokens + calls `onSessionExpired` → `AuthContext` logs out.

**Screens / Components**
- `src/app/index.tsx`, `explore.tsx`, `login.tsx`
- `src/components/ui/*` (Card, Button, TextInput, collapsible), `app-tabs` (+ `.web` variant), `themed-view/text`, `add-item-modal`, `item-detail-modal`, `animated-icon`

---

## 4. Important Folders & Files

| Path | Role |
|------|------|
| `backend/config/settings/base.py` | Single source of truth for apps, middleware, DRF/JWT/Celery, `AUTH_USER_MODEL`, `.env.base` loading |
| `backend/config/settings/production.py` | Prod hardening (HSTS, `SECURE_PROXY_SSL_HEADER`, WhiteNoise, logging); **currently modified** |
| `backend/config/urls.py` | API mount points |
| `backend/config/celery.py` | Celery app + autodiscover |
| `backend/apps/users/models.py` | `CustomUser` |
| `backend/apps/users/views.py` + `serializers.py` + `services.py` + `tasks.py` | Auth flow + profile + premium expiry |
| `backend/apps/saved_items/models.py` | Domain models + `visible_to()` + constraints |
| `backend/apps/saved_items/views.py` | `CategoryViewSet` / `SavedItemViewSet` |
| `backend/apps/saved_items/serializers.py` | Validation + ownership checks |
| `backend/apps/saved_items/services.py` | Transactional business logic + queueing |
| `backend/apps/saved_items/filters.py` | `SavedItemFilter` (django-filter) |
| `backend/apps/saved_items/extraction/` | Fetcher / parser / pipeline / security |
| `backend/apps/saved_items/tasks.py` | `extract_content_task` + `purge_expired_completed_items` |
| `backend/apps/saved_items/admin.py` | Django admin; **currently modified** |
| `backend/apps/core/pagination.py` | `StandardPagination` |
| `frontend/src/app/_layout.tsx` | Root layout + auth gate |
| `frontend/src/api/client.js` | Axios + refresh logic (**hardcoded LAN IP** — must become env var) |
| `frontend/src/context/AuthContext.tsx` | Auth state |
| `frontend/app.json` | Expo config (plugins: `expo-router`, `expo-splash-screen`, `expo-secure-store`) |
| `frontend/AGENTS.md` | Expo contribution rules (SDK 57) |
| `frontend/package.json` | Expo deps — install with `npx expo install` |
| `.gitignore` | Ignores `.env*`, `.venv`, `db.sqlite3`, `frontend/node_modules` |

---

## 5. What to Know Before Making Changes

1. **Dirty working tree** — `backend/apps/saved_items/admin.py` and `backend/config/settings/production.py` are `M` (modified, unstaged); `frontend/` is `??` (untracked). Branch `master`. Avoid `git add -A`; stage explicitly.
2. **Env files** — `backend/.env.base` (required: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL`/`DJANGO_ALLOWED_HOSTS`, `CELERY_BROKER_URL`) and `.env.production`; never commit them.
3. **Tenancy is mandatory** — every queryset must be scoped via `visible_to(user)` / `user=`; `Category.name` is unique *per user*; `SavedItemCategory` validates `category.user_id == request.user.id`.
4. **JWT rotation** — `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` enabled; logout blacklists; refresh failures must clear `SecureStore`.
5. **Extraction is best-effort** — `run_extraction` never raises for expected failures; stale tasks are dropped via `extraction_version`; broker unavailability is handled inside `transaction.on_commit`.
6. **DB constraints matter** — `name_or_url_required` and `status/completed_at` consistency are enforced at the DB; serializer `validate()` mirrors them — keep in sync.
7. **Frontend `BASE_URL`** — `src/api/client.js` hardcodes `http://10.187.251.107:8000/api/v1`; replace with `expo-constants` / `EXPO_PUBLIC_*` env before any production build.
8. **Expo rules** — routes must live in `src/app/` (every file is a route, `_layout.tsx` defines navigators); non-route code stays outside `src/app/`; prefer Expo modules over third-party native libs; after adding native code a dev build is required (`npx expo run:ios|android` or `eas build --profile development`).
9. **Verification** — backend: `python manage.py check` / `pytest` (if configured); frontend: `npx tsc --noEmit` + `npx expo lint` + `npx expo-doctor` (per `AGENTS.md`).
10. **Prod security** — `SECURE_SSL_REDIRECT`, `HSTS` (default 86400 — raise only after HTTPS verified), `CSRF_TRUSTED_ORIGINS`, CORS (currently commented out — enable deliberately if needed); WhiteNoise is inserted after `SecurityMiddleware`.
