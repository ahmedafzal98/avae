"use client";

import { useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { AuditTarget } from "@/types/audit-target";
import { AUDIT_TARGETS } from "@/types/audit-target";

export interface AuditTargetSelectProps {
  value: AuditTarget;
  onValueChange: (value: AuditTarget) => void;
  disabled?: boolean;
  className?: string;
}

export function AuditTargetSelect({
  value,
  onValueChange,
  disabled = false,
  className,
}: AuditTargetSelectProps) {
  // MVP: Ensure default/fallback is companies_house (only active target)
  const effectiveValue =
    value && AUDIT_TARGETS.some((t) => t.value === value && t.available)
      ? value
      : "companies_house";

  // Sync parent state when value is invalid (e.g. persisted "epc" from before MVP)
  useEffect(() => {
    if (value && !AUDIT_TARGETS.find((t) => t.value === value && t.available)) {
      onValueChange("companies_house");
    }
  }, [value, onValueChange]);

  return (
    <Select
      value={effectiveValue}
      onValueChange={(v) => v && onValueChange(v as AuditTarget)}
      disabled={disabled}
    >
      <SelectTrigger
        className={cn(
          "w-full border-[#e2e8f0] bg-white text-foreground placeholder:text-muted-foreground hover:bg-white focus-visible:border-[#475569] focus-visible:ring-[#475569]/30",
          className
        )}
        size="default"
      >
        <SelectValue placeholder="Select target database..." />
      </SelectTrigger>
      <SelectContent>
        {AUDIT_TARGETS.map(({ value: v, label, available }) => (
          <SelectItem key={v} value={v} disabled={!available}>
            {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
