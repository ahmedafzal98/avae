"use client";

import { CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { VerificationStatus } from "@/types/api";

const statusConfig: Record<
  string,
  { label: string; icon: typeof CheckCircle; className: string }
> = {
  VERIFIED: {
    label: "Verified",
    icon: CheckCircle,
    className: "bg-tertiary/15 text-tertiary border-tertiary/30",
  },
  DISCREPANCY: {
    label: "Discrepancy",
    icon: AlertTriangle,
    className: "bg-destructive/15 text-destructive border-destructive/30",
  },
  DISCREPANCY_FLAG: {
    label: "Discrepancy",
    icon: AlertTriangle,
    className: "bg-destructive/15 text-destructive border-destructive/30",
  },
  PENDING: {
    label: "Pending",
    icon: Clock,
    className: "bg-warning/15 text-warning border-warning/30",
  },
  PENDING_HUMAN_REVIEW: {
    label: "Pending Review",
    icon: Clock,
    className: "bg-warning/15 text-warning border-warning/30",
  },
  AWAITING_CLIENT_REMEDIATION: {
    label: "Awaiting Client",
    icon: Clock,
    className: "bg-warning/15 text-warning border-warning/30",
  },
};

interface StatusBadgeProps {
  status: VerificationStatus | string;
  showIcon?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  showIcon = true,
  className,
}: StatusBadgeProps) {
  const config =
    statusConfig[status] ??
    statusConfig.PENDING;

  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={cn(
        "font-medium border transition-colors duration-150",
        config.className,
        className
      )}
    >
      {showIcon && <Icon className="size-3.5 shrink-0" aria-hidden />}
      {config.label}
    </Badge>
  );
}
