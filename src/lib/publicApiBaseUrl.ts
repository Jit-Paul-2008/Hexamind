/**
 * Browser-visible backend origin. Next.js inlines NEXT_PUBLIC_* at build time.
 * NEXT_PUBLIC_API_URL is accepted for setups that followed older docs/scripts.
 */
export const publicApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";
