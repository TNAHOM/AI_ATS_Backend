# Clerk + FastAPI Auth Integration Guide (Frontend + Backend Contract)

This guide explains:
- what the backend currently handles for Clerk auth,
- what the frontend must send/handle,
- and how to integrate both sides safely for production.

It is aligned with the current backend implementation in:
- `app/core/security.py`
- `app/dependencies.py`
- `.env.example`

And validated against current Clerk docs references:
- Session tokens and claims: https://clerk.com/docs/guides/sessions/session-tokens
- Next.js `auth()` reference: https://clerk.com/docs/references/nextjs/auth

---

## 1) Backend auth behavior (what backend already handles)

### 1.1 Token input format
Backend only accepts:

`Authorization: Bearer <token>`

If missing/invalid scheme:
- `401` `AUTH_MISSING_BEARER_TOKEN`

### 1.2 Signature and JWT validation
Backend verifies session JWTs using Clerk JWKS:

- Algorithm required: `RS256`
- `kid` required in JWT header
- JWKS fetched from `CLERK_JWKS_URL`
- JWKS cached in memory with TTL (`CLERK_JWKS_CACHE_TTL_SECONDS`)
- If `CLERK_JWKS_URL` is unset, backend derives it from:
  - `CLERK_ISSUER + "/.well-known/jwks.json"`

Claims verification:
- Required: `sub`, `iss`, `exp`, `iat`
- `nbf` is verified
- `iss` must match `CLERK_ISSUER`
- `aud` is verified only when `CLERK_AUDIENCE` is set
- Expired token: `401` `AUTH_TOKEN_EXPIRED`
- Other token problems: `401` `AUTH_INVALID_TOKEN`

### 1.3 Provisioning and account checks
After JWT validation, backend resolves internal user:

1. Reads email from:
   - `email` claim first
   - fallback: first entry of `email_addresses`
2. Looks up internal `User` by email
3. Requires internal user to exist and be active

Errors:
- Missing required email claim: `401` `AUTH_MISSING_EMAIL_CLAIM`
- No matching internal user: `403` `AUTH_USER_NOT_PROVISIONED`
- Internal user inactive: `403` `AUTH_INACTIVE_USER`

### 1.4 Auth context passed to routes
On success, dependency returns:
- `clerk_id`
- `email`
- `internal_user_id`
- `is_active`
- `is_superuser`

Superuser-only routes enforce:
- `403` `AUTH_FORBIDDEN` when user is not superuser

---

## 2) What frontend must do

### 2.1 Always send bearer token for protected FastAPI routes
For protected backend routes, frontend must send:

`Authorization: Bearer <Clerk session token>`

Do not rely on Clerk cookies directly for cross-origin FastAPI calls.

### 2.2 Use a JWT template for backend API calls
Create a Clerk JWT template (for example `backend-api`) and use it consistently for backend requests.

Recommended template settings:
- **Custom signing key**: OFF (recommended)
- **Audience**: set explicitly (example: `https://api.yourapp.com`)
- **Issuer/JWKS**: keep Clerk defaults for your instance

Audience note:
- `aud` is an identifier string, not a required reachable URL.
- You can use values like `api://ai-ats-backend` (prod identifier), `https://api.yourapp.com` (prod URL-style identifier), or `api://ai-ats-dev` (development identifier).

Why keep custom signing key OFF:
- This backend already validates Clerk-issued RS256 tokens using Clerk JWKS.
- Keeping Clerk-managed signing avoids extra key rotation/secret distribution overhead.
- Only enable custom signing key if you explicitly need external key management and can operate rotation safely.

In **Customize session token**, include at least:

```json
{
  "aud": "https://api.yourapp.com",
  "email": "{{user.primary_email_address}}"
}
```

Why:
- Backend requires `email` claim for user resolution.
- Backend validates `aud` when `CLERK_AUDIENCE` is configured.

### 2.3 Keep env values aligned between Clerk and backend
In backend `.env`:

- `CLERK_ISSUER` = your instance issuer domain
- `CLERK_JWKS_URL` = **recommended unset** (backend auto-derives from `CLERK_ISSUER`)
  - Set it explicitly only if you intentionally need a non-standard/custom JWKS endpoint
- `CLERK_AUDIENCE` = exact value configured in JWT template audience

If token `aud` and backend `CLERK_AUDIENCE` mismatch, requests fail with `401 AUTH_INVALID_TOKEN`.

JWKS troubleshooting:
- If JWT verification fails with JWKS fetch errors, verify:
  1. `CLERK_ISSUER` is a valid Clerk issuer URL,
  2. derived URL `<CLERK_ISSUER>/.well-known/jwks.json` is reachable from backend runtime,
  3. your runtime can resolve and reach Clerk over HTTPS.

### 2.4 Provision internal backend user early
A valid Clerk token is not enough by itself.
Frontend must ensure backend user provisioning happens immediately after sign-up/sign-in (before protected business calls).

Important note:
- This repository currently enforces the provisioning check in auth dependencies.
- If your backend does not yet expose a dedicated self-provision endpoint, add one (or call your existing onboarding endpoint) and run it right after successful Clerk sign-in.
- The minimum payload should contain the user email used for backend lookup plus any required profile metadata.

---

## 3) End-to-end integration flow

1. User signs in with Clerk in Next.js.
2. Frontend requests backend token from Clerk template (`backend-api`).
3. Frontend sends token in `Authorization: Bearer ...` to FastAPI.
4. Backend verifies JWT (signature + claims).
5. Backend resolves internal user by email and checks active status.
6. API returns data if user is provisioned and active.

---

## 4) Error contract frontend should implement

- `401 AUTH_MISSING_BEARER_TOKEN` → request bug; attach token
- `401 AUTH_INVALID_TOKEN` / `AUTH_TOKEN_EXPIRED` → refresh token or re-authenticate
- `401 AUTH_MISSING_EMAIL_CLAIM` → JWT template misconfiguration (missing email claim)
- `403 AUTH_USER_NOT_PROVISIONED` → run onboarding/provisioning flow
- `403 AUTH_INACTIVE_USER` → show blocked-account state
- `403 AUTH_FORBIDDEN` → user lacks role/permission

---

## 5) Next.js example (Clerk v7+)

### 5.1 Server-side call (Route Handler / Server Action)
```ts
import { auth } from "@clerk/nextjs/server";

export async function GET() {
  const { getToken } = await auth();
  const token = await getToken({ template: "backend-api" });

  if (!token) {
    return new Response("Unauthenticated", { status: 401 });
  }

  const response = await fetch(`${process.env.BACKEND_URL}/jobs/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  const data = await response.json();
  return Response.json(data, { status: response.status });
}
```

### 5.2 Client-side call (Browser)
```ts
import { useAuth } from "@clerk/nextjs";

export function useBackendApi() {
  const { getToken } = useAuth();

  const callBackend = async (path: string, init?: RequestInit) => {
    const request = async (token: string) =>
      fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}${path}`, {
        ...init,
        headers: {
          ...(init?.headers ?? {}),
          Authorization: `Bearer ${token}`,
        },
      });

    let token = await getToken({ template: "backend-api" });
    if (!token) throw new Error("No auth token available");

    let response = await request(token);

    // One safe retry on 401 with a freshly requested token.
    if (response.status === 401) {
      token = await getToken({ template: "backend-api", skipCache: true });
      if (!token) throw new Error("No auth token available");
      response = await request(token);
    }

    return response;
  };

  return { callBackend };
}
```

Provisioning handshake example (frontend-side pseudocode):
```ts
const { getToken } = useAuth();
const token = await getToken({ template: "backend-api" });
await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/your-provision-endpoint`, {
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  method: "POST",
  body: JSON.stringify({
    // include fields your backend provisioning endpoint requires
  }),
});
```

---

## 6) Quick verification checklist

- [ ] JWT template exists (e.g., `backend-api`)
- [ ] Template includes `aud` and `email` claims
- [ ] Frontend uses `getToken({ template: "backend-api" })`
- [ ] Frontend sends `Authorization: Bearer <token>`
- [ ] `CLERK_ISSUER` matches your Clerk instance issuer domain
- [ ] `CLERK_AUDIENCE` matches JWT template audience value exactly
- [ ] `CLERK_JWKS_URL` is unset (recommended), or explicitly set only for a non-standard JWKS endpoint
- [ ] Protected endpoint call succeeds for provisioned active user
- [ ] Expected 401/403 errors are handled in frontend UX
