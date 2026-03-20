import Link from "next/link";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { AppHeader } from "@/components/layout/AppHeader";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary>
    <div className="flex min-h-screen">
      {/* Task 8.1: Skip to main content for keyboard navigation */}
      <Link
        href="#main-content"
        className="sr-only focus:absolute focus:left-4 focus:top-4 focus:z-100 focus:m-0 focus:h-auto focus:w-auto focus:overflow-visible focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:[clip:auto]"
      >
        Skip to main content
      </Link>
      <AppSidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <AppHeader />
        <main
          id="main-content"
          className="flex-1 overflow-auto bg-[#f8fafc]"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
    </ErrorBoundary>
  );
}
