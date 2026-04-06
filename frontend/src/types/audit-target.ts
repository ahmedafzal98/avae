/** Audit targets for compliance verification — must match backend API */
export type AuditTarget =
  | "epc"
  | "companies_house"
  | "hm_land_registry"
  | "financial"
  | "vision_poc";

/** MVP: Companies House + multimodal vision POC. Others on roadmap. */
export const AUDIT_TARGETS: { value: AuditTarget; label: string; available: boolean }[] = [
  { value: "companies_house", label: "Companies House", available: true },
  {
    value: "vision_poc",
    label: "Vision POC (GPT-4o — IDs, Arabic/mixed docs, no registry check)",
    available: true,
  },
  { value: "epc", label: "EPC (Energy Performance Certificate) — Coming soon", available: false },
  { value: "hm_land_registry", label: "HM Land Registry — Coming soon", available: false },
  { value: "financial", label: "Financial Statements — Coming soon", available: false },
];
