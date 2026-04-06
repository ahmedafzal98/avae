"use client";

import { cn } from "@/lib/utils";
import {
  containsArabicScript,
  isVisionPocArabicPrimaryField,
  westernDigitsToArabicIndic,
} from "@/lib/vision-poc-display";

function formatScalar(val: unknown): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "string") return val;
  if (typeof val === "number" || typeof val === "boolean") return String(val);
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export function ExtractedValue({
  value,
  field,
  className,
}: {
  value: unknown;
  field: string;
  className?: string;
}) {
  const s = formatScalar(value);
  if (!s.trim()) {
    return <span className="text-slate-400">—</span>;
  }

  const lower = field.toLowerCase();
  const forceEn = lower.includes("_english");
  const forceAr = lower.includes("_arabic");
  const arabicPrimaryNumeric = isVisionPocArabicPrimaryField(field);
  const arabicInValue = containsArabicScript(s);

  /** IDs & dates: show Eastern Arabic numerals + RTL even when extraction used 0–9 */
  if (arabicPrimaryNumeric) {
    const displayed = westernDigitsToArabicIndic(s);
    return (
      <p
        dir="rtl"
        lang="ar"
        className={cn(
          "font-[family-name:var(--font-arabic)] text-base font-medium tabular-nums leading-relaxed text-slate-900",
          className
        )}
      >
        {displayed}
      </p>
    );
  }

  if (forceAr) {
    return (
      <p
        dir="rtl"
        lang="ar"
        className={cn(
          "font-[family-name:var(--font-arabic)] text-base leading-relaxed text-slate-900",
          className
        )}
      >
        {s}
      </p>
    );
  }

  if (forceEn) {
    return (
      <p
        dir="ltr"
        lang="en"
        className={cn("text-base font-medium text-slate-900", className)}
      >
        {s}
      </p>
    );
  }

  if (arabicInValue) {
    return (
      <p
        dir="auto"
        className={cn(
          "text-base text-slate-900",
          "font-[family-name:var(--font-arabic)] leading-relaxed",
          className
        )}
      >
        {s}
      </p>
    );
  }

  return (
    <p
      dir="ltr"
      lang="en"
      className={cn("text-base font-medium text-slate-900", className)}
    >
      {s}
    </p>
  );
}
