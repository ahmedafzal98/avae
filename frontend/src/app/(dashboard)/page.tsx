import { DashboardMetrics } from "@/components/dashboard/DashboardMetrics";
import { ComplianceHealthChart } from "@/components/dashboard/ComplianceHealthChart";
import { AuditTrail } from "@/components/dashboard/AuditTrail";
import { VerificationQueueTable } from "@/components/dashboard/VerificationQueueTable";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#f8fafc] p-8">
      <div className="mx-auto max-w-7xl">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-[#64748b]">
            Agentic Verification and Audit Engine — compliance & audit platform
          </p>
        </div>

        {/* Metric row — real data from API */}
        <DashboardMetrics />

        {/* Analytics row — 70/30 split */}
        <div className="mb-8 grid gap-6 lg:grid-cols-[1fr_340px]">
          <ComplianceHealthChart />
          <AuditTrail />
        </div>

        {/* Table section */}
        <VerificationQueueTable />
      </div>
    </div>
  );
}
