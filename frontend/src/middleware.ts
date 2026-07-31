import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { isDevAuthBypass } from "@/lib/dev-auth";

const isProtectedRoute = createRouteMatcher([
  "/",
  "/upload(.*)",
  "/api/upload(.*)",
  "/audit(.*)",
  "/settings(.*)",
  "/verification(.*)",
  "/hitl(.*)",
]);

const clerkAuth = clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export default function middleware(req: NextRequest) {
  if (isDevAuthBypass()) {
    return NextResponse.next();
  }
  return clerkAuth(req);
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
