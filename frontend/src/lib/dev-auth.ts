/**
 * Local development: skip Clerk when keys are placeholders or DEV_SKIP_AUTH is set.
 * Set NEXT_PUBLIC_DEV_SKIP_AUTH=true in .env.local (auto-enabled for example keys).
 */
export function isDevAuthBypass(): boolean {
  if (process.env.NEXT_PUBLIC_DEV_SKIP_AUTH === "true") {
    return true;
  }
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
  return (
    !key ||
    key.includes("your_publishable_key") ||
    key.includes("your-secret") ||
    key === "pk_test_your_publishable_key"
  );
}
