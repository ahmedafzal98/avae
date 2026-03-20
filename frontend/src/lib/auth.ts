/**
 * Auth helpers — abstracts token retrieval for API calls.
 *
 * Current: Clerk. See docs/AVAE_AUTH_JS_MIGRATION.md for Auth.js migration.
 */
"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useCallback } from "react";

/**
 * Returns a function to fetch the current session token for API requests.
 * Use with apiFetch / apiJson: const getToken = useAuthToken(); const token = await getToken();
 */
export function useAuthToken(): () => Promise<string | null> {
  const { getToken } = useAuth();
  return useCallback(() => getToken(), [getToken]);
}

/**
 * Returns display string for "AUTHORIZED AS [Officer Level]" (Task 6.8).
 * Uses a role label (from Clerk or "Compliance Officer"); appends email in parentheses when available.
 */
export function useOfficerLevel(): string {
  const { user } = useUser();
  const role = user?.publicMetadata?.role;
  const email = user?.primaryEmailAddress?.emailAddress;
  const roleLabel = typeof role === "string" && role ? role : "Compliance Officer";
  return email ? `${roleLabel} (${email})` : roleLabel;
}
