/**
 * Authority-based labels for compliance UI.
 * Translates technical audit_target values into enterprise-friendly registry names.
 */

export function getOfficialRegistryName(auditTarget: string): string {
  switch (auditTarget?.toLowerCase()) {
    case "companies_house":
      return "Official Company Record";
    case "hm_land_registry":
      return "Official Title Record";
    case "epc":
      return "EPC Register";
    case "financial":
      return "SEC EDGAR";
    default:
      return "Official Record";
  }
}

/** Subtitle for credibility: "Verified against Companies House" */
export function getVerifiedAgainstLabel(auditTarget: string): string {
  switch (auditTarget?.toLowerCase()) {
    case "companies_house":
      return "Verified against Companies House";
    case "hm_land_registry":
      return "Verified against HM Land Registry";
    case "epc":
      return "Verified against EPC Register";
    case "financial":
      return "Verified against SEC EDGAR";
    default:
      return "Verified from official records";
  }
}

/** Source badge: government vs financial (no API jargon) */
export function getSourceBadgeLabel(auditTarget: string): string {
  switch (auditTarget?.toLowerCase()) {
    case "financial":
      return "Verified from financial records";
    case "companies_house":
    case "hm_land_registry":
    case "epc":
    default:
      return "Verified from government records";
  }
}

/** Emoji for source badge: 🏛️ government, 🏦 financial */
export function getSourceBadgeEmoji(auditTarget: string): string {
  return auditTarget?.toLowerCase() === "financial" ? "🏦" : "🏛️";
}

/** Format ISO timestamp for "Live sync" display (e.g. "Today, 09:41 AM") */
export function formatLiveSyncTimestamp(isoString: string | null | undefined): string {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    const now = new Date();
    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear();
    const timeStr = date.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return isToday ? `Today, ${timeStr}` : date.toLocaleDateString(undefined, { dateStyle: "short" }) + ", " + timeStr;
  } catch {
    return "";
  }
}
