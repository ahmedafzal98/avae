"use client";

import { Bell, HelpCircle, User } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Header user area when Clerk is bypassed for local dev. */
export function DevAuthHeader() {
  return (
    <>
      <div className="flex items-center gap-2 text-body text-muted-foreground">
        <span className="hidden sm:inline">Dev mode (no Clerk)</span>
        <span
          className="size-2 rounded-full bg-amber-500"
          aria-hidden
          title="Auth bypassed"
        />
      </div>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon-sm" aria-label="Notifications">
          <Bell className="size-4" />
        </Button>
        <Button variant="ghost" size="icon-sm" aria-label="Help">
          <HelpCircle className="size-4" />
        </Button>
      </div>
      <div
        className="flex size-8 items-center justify-center rounded-full bg-muted"
        aria-label="Dev user"
      >
        <User className="size-4 text-muted-foreground" />
      </div>
    </>
  );
}
