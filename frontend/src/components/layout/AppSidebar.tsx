"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  ShieldCheck,
  FileText,
  Settings,
  Menu,
  HelpCircle,
  Shield,
} from "lucide-react";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/hitl", label: "Verification", icon: ShieldCheck },
  { href: "/audit", label: "Audit Log", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

function NavLinks({
  pathname,
  className,
  onNavigate,
  asDropdownItems,
}: {
  pathname: string;
  className?: string;
  onNavigate?: () => void;
  asDropdownItems?: boolean;
}) {
  const items = navItems.map(({ href, label, icon: Icon }) => {
    const isActive =
      href === "/" ? pathname === "/" : pathname.startsWith(href);
    const content = (
      <>
        <Icon
          className={cn(
            "size-5 shrink-0 transition-colors",
            isActive ? "text-[#0f172a]" : "text-[#64748b] group-hover:text-[#0f172a]"
          )}
          aria-hidden
        />
        <span>{label}</span>
      </>
    );
    if (asDropdownItems) {
      return (
        <DropdownMenuItem key={href}>
          <Link
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex w-full items-center gap-3 rounded-md py-2.5 px-3",
              isActive && "font-medium"
            )}
          >
            {content}
          </Link>
        </DropdownMenuItem>
      );
    }
    return (
      <Link
        key={href}
        href={href}
        onClick={onNavigate}
        className={cn(
          "group flex h-11 items-center gap-3 rounded-md px-3 font-medium transition-colors",
          isActive
            ? "border-l-2 border-l-[#0f172a] bg-[#e2e8f0] text-[#0f172a]"
            : "text-[#475569] hover:bg-[#f1f5f9] hover:text-[#0f172a]",
          className
        )}
        aria-current={isActive ? "page" : undefined}
      >
        {content}
      </Link>
    );
  });
  return <>{items}</>;
}

export function AppSidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Task 8.8: Mobile menu button — visible only on small screens */}
      <div className="fixed left-4 top-20 z-40 md:hidden">
        <DropdownMenu open={mobileOpen} onOpenChange={setMobileOpen}>
          <DropdownMenuTrigger
            render={
              <button
                type="button"
                className={cn(
                  "inline-flex size-7 shrink-0 items-center justify-center rounded-lg border border-input bg-background text-foreground hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  "aria-expanded:bg-muted aria-expanded:text-foreground"
                )}
                aria-label="Open navigation menu"
                aria-haspopup="menu"
              >
                <Menu className="size-5" />
              </button>
            }
          />
          <DropdownMenuContent align="start" className="w-56">
            <NavLinks
              pathname={pathname}
              onNavigate={() => setMobileOpen(false)}
              asDropdownItems
            />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Desktop sidebar — 260px, Slate 50, Slate 200 border */}
      <aside
        className="hidden h-screen w-[260px] shrink-0 flex-col border-r border-[#e2e8f0] bg-[#f8fafc] py-6 px-4 md:flex"
        aria-label="Main navigation"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center gap-3 pb-6">
          <div
            className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#0f172a] text-white"
            aria-hidden
          >
            <Shield className="size-5" />
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="text-sm font-bold text-[#0f172a]">
              AVAE Engine
            </span>
            <span className="text-[11px] font-normal text-[#64748b]">
              Compliance & Audit
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav
          className="flex flex-1 flex-col gap-1 overflow-auto"
          role="navigation"
        >
          <NavLinks pathname={pathname} />
        </nav>

        {/* Footer */}
        <div className="mt-auto shrink-0 border-t border-[#e2e8f0] pt-4">
          <Link
            href="/support"
            className="group flex h-11 items-center gap-3 rounded-md px-3 font-medium text-[#475569] transition-colors hover:bg-[#f1f5f9] hover:text-[#0f172a]"
          >
            <HelpCircle className="size-5 shrink-0 text-[#64748b] transition-colors group-hover:text-[#0f172a]" aria-hidden />
            Support
          </Link>
        </div>
      </aside>
    </>
  );
}
