"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, HelpCircle } from "lucide-react";
import { UserButton, SignInButton, Show } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AppHeaderProps {
  /** Optional override for breadcrumb (e.g. page-specific title) */
  title?: string;
}

export function AppHeader({ title }: AppHeaderProps) {
  const pathname = usePathname();

  return (
    <header
      className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-background px-4 sm:px-6"
      role="banner"
    >
      <span className="text-body font-medium text-foreground shrink-0">
        Verification & Audit
      </span>

      <div className="flex flex-1 max-w-md mx-auto">
        <Input
          type="search"
          placeholder="Search records..."
          className="h-9 w-full rounded-lg bg-muted/50 border-border"
          aria-label="Search records"
        />
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <Show when="signed-out">
          <SignInButton mode="redirect" forceRedirectUrl="/">
            <Button variant="outline" size="sm">
              Sign in
            </Button>
          </SignInButton>
        </Show>
        <Show when="signed-in">
          <div className="flex items-center gap-2 text-body text-muted-foreground">
            <span className="hidden sm:inline">UK Financial Services</span>
            <span
              className="size-2 rounded-full bg-tertiary"
              aria-hidden
              title="Online"
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
          <UserButton
            appearance={{
              elements: {
                avatarBox: "size-8",
              },
            }}
          />
        </Show>
      </div>
    </header>
  );
}
