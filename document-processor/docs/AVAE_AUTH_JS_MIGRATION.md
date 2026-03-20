# Auth.js Migration Path — AVAE Frontend

**Status:** Optional fallback (Task 3.6)  
**Current:** Clerk  
**Target:** Auth.js (self-hosted)

Use this document if you prefer self-hosted auth over Clerk’s SaaS. Auth.js gives full control over user data and no vendor lock-in, at the cost of more setup for MFA/SSO.

---

## 1. Current Clerk Setup

| File | Purpose |
|------|---------|
| `app/layout.tsx` | `ClerkProvider` wraps app |
| `middleware.ts` | `clerkMiddleware` + `createRouteMatcher` for protected routes |
| `app/(auth)/sign-in/[[...sign-in]]/page.tsx` | Clerk `<SignIn />` |
| `app/(auth)/sign-up/[[...sign-up]]/page.tsx` | Clerk `<SignUp />` |
| `components/layout/AppHeader.tsx` | `SignInButton`, `UserButton`, `Show` (signed-in/out) |
| `lib/auth.ts` | `useAuthToken()` — returns `getToken` for API calls |
| `lib/api.ts` | `apiFetch` / `apiJson` accept `token` from `useAuthToken()` |

**Env vars:** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`

---

## 2. Auth.js Equivalents

| Clerk | Auth.js |
|-------|---------|
| `ClerkProvider` | `SessionProvider` (client) + `auth()` (server) |
| `clerkMiddleware` | `auth` middleware from `auth.config.ts` |
| `<SignIn />` | Custom sign-in page or Auth.js UI |
| `<SignUp />` | Custom sign-up page |
| `useAuth().getToken()` | `auth()` → `session` → JWT or `getToken()` |
| `Show when="signed-in"` | `session ? <UserButton /> : null` |
| `UserButton` | Custom dropdown + `signOut()` |

---

## 3. Migration Steps

### 3.1 Install Auth.js

```bash
npm uninstall @clerk/nextjs
npm install next-auth@beta
```

Auth.js v5 uses the `next-auth` package (beta).

### 3.2 Auth Configuration

Create `auth.config.ts` at project root:

```ts
import type { NextAuthConfig } from "next-auth";

export const authConfig = {
  pages: {
    signIn: "/sign-in",
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isProtected =
        nextUrl.pathname.startsWith("/upload") ||
        nextUrl.pathname.startsWith("/audit") ||
        nextUrl.pathname.startsWith("/settings") ||
        nextUrl.pathname.startsWith("/verification") ||
        nextUrl.pathname.startsWith("/hitl");
      if (isProtected && !isLoggedIn) return Response.redirect(new URL("/sign-in", nextUrl));
      return true;
    },
  },
  providers: [], // Add Credentials, Google, etc.
} satisfies NextAuthConfig;
```

Create `auth.ts` (wraps `NextAuth` with config):

```ts
import NextAuth from "next-auth";
import { authConfig } from "./auth.config";

export const { auth, signIn, signOut, handlers } = NextAuth(authConfig);
```

### 3.3 Middleware

Replace `middleware.ts`:

```ts
import { auth } from "@/auth";

export default auth((req) => {
  // authConfig.authorized handles protection
  return;
});

export const config = {
  matcher: ["/((?!_next|sign-in|sign-up|[^?]*\\.(?:html?|css|js(?!on)|...)).*)"],
};
```

### 3.4 Root Layout

Replace `ClerkProvider` with `SessionProvider`:

```tsx
// app/layout.tsx
import { SessionProvider } from "next-auth/react";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
```

### 3.5 Sign-In / Sign-Up Pages

Replace Clerk components with custom forms or Auth.js UI:

```tsx
// app/(auth)/sign-in/page.tsx
"use client";
import { signIn } from "next-auth/react";

export default function SignInPage() {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const form = e.target as HTMLFormElement;
        signIn("credentials", {
          email: form.email.value,
          password: form.password.value,
          callbackUrl: "/",
        });
      }}
    >
      <input name="email" type="email" />
      <input name="password" type="password" />
      <button type="submit">Sign in</button>
    </form>
  );
}
```

### 3.6 AppHeader

Replace Clerk components with `useSession`:

```tsx
"use client";
import { useSession, signIn, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const { data: session, status } = useSession();

  return (
    <header>
      {/* ... breadcrumb ... */}
      {status === "loading" ? null : session ? (
        <button onClick={() => signOut({ callbackUrl: "/" })}>
          Sign out
        </button>
      ) : (
        <Button onClick={() => signIn(undefined, { callbackUrl: "/" })}>
          Sign in
        </Button>
      )}
    </header>
  );
}
```

### 3.7 API Token Injection & lib/auth.ts

The app uses `lib/auth.ts` → `useAuthToken()` for token retrieval. Replace it when migrating:

```ts
// lib/auth.ts (Auth.js version)
"use client";

import { useSession } from "next-auth/react";
import { useCallback } from "react";

export function useAuthToken(): () => Promise<string | null> {
  const { data: session } = useSession();
  return useCallback(async () => {
    // If using JWT strategy with accessToken in session
    return (session as { accessToken?: string })?.accessToken ?? null;
  }, [session]);
}
```

Auth.js can provide a JWT via the `jwt` callback. Ensure your adapter/session strategy returns a token:

```ts
// auth.config.ts callbacks
jwt({ token, user }) {
  if (user) token.id = user.id;
  return token;
},
session({ session, token }) {
  if (session.user) session.user.id = token.id;
  return session;
},
```

Then in hooks (unchanged):

```ts
const getToken = useAuthToken();
const token = await getToken();
const data = await apiJson("/documents", { token });
```

---

## 4. Env Vars

| Clerk | Auth.js |
|-------|---------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | — |
| `CLERK_SECRET_KEY` | `AUTH_SECRET` |
| — | `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET` (if using Google) |

---

## 5. Trade-offs

| Consideration | Clerk | Auth.js |
|---------------|-------|---------|
| MFA / SSO | Built-in | Manual setup |
| SAML | Simple | More configuration |
| Hosting | SaaS | Self-hosted |
| Compliance | SOC 2, GDPR | DIY |
| Setup time | Low | Higher |

**Recommendation:** Stay on Clerk for speed and compliance unless self-hosting is required. Use this doc when migrating.
