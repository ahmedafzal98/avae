import type { VerificationFieldRow } from "@/lib/api";

/** Arabic script ranges (simplified) */
export function containsArabicScript(text: string): boolean {
  return /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(
    text
  );
}

/** Arabic-Indic digits (٠١٢٣…) — standard for Gulf IDs and Arabic UI */
const ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

/**
 * Replace Western digits 0–9 with Arabic-Indic equivalents; leave other chars unchanged.
 */
export function westernDigitsToArabicIndic(input: string): string {
  return input.replace(/[0-9]/g, (ch) => {
    const n = ch.charCodeAt(0) - 0x30;
    return n >= 0 && n <= 9 ? ARABIC_INDIC_DIGITS[n]! : ch;
  });
}

/**
 * ID numbers, passport numbers, and dates on Arabic documents are often extracted as
 * Western digits; we display them with Arabic-Indic numerals and RTL for readability.
 */
export function isVisionPocArabicPrimaryField(field: string): boolean {
  const f = field.toLowerCase();
  return (
    f === "id_number" ||
    f === "passport_number" ||
    f === "date_of_birth" ||
    f === "issue_date" ||
    f === "expiry_date"
  );
}

/** Arabic subtitles for field headers (Vision POC single cards) */
export const VISION_POC_FIELD_LABEL_AR: Record<string, string> = {
  document_type: "نوع المستند",
  document_title: "عنوان المستند",
  id_number: "رقم الهوية / الإقامة",
  passport_number: "رقم جواز السفر",
  nationality: "الجنسية",
  gender: "الجنس",
  religion: "الديانة",
  date_of_birth: "تاريخ الميلاد",
  issue_date: "تاريخ الإصدار",
  expiry_date: "تاريخ الانتهاء / الصلاحية",
  employer_or_sponsor: "جهة العمل / الكفيل",
  occupation: "المهنة",
  address: "العنوان",
  agreement_or_contract_subject: "موضوع الاتفاقية",
  additional_notes: "ملاحظات إضافية",
};

export function visionPocFieldLabelArabic(field: string): string | undefined {
  return VISION_POC_FIELD_LABEL_AR[field.toLowerCase()];
}

export type VisionPocDisplayItem =
  | {
      kind: "name_pair" | "party_pair";
      key: string;
      label: string;
      labelAr: string;
      english?: VerificationFieldRow;
      arabic?: VerificationFieldRow;
    }
  | { kind: "single"; row: VerificationFieldRow };

type EnArPairDef = {
  en: string;
  ar: string;
  label: string;
  labelAr: string;
};

const NAME_PAIR: EnArPairDef = {
  en: "full_name_english",
  ar: "full_name_arabic",
  label: "Full name",
  labelAr: "الاسم الكامل",
};

const PARTY_ONE: EnArPairDef = {
  en: "party_one_name_english",
  ar: "party_one_name_arabic",
  label: "Party one",
  labelAr: "الطرف الأول",
};

const PARTY_TWO: EnArPairDef = {
  en: "party_two_name_english",
  ar: "party_two_name_arabic",
  label: "Party two",
  labelAr: "الطرف الثاني",
};

/**
 * Group English/Arabic pairs into bilingual cards; remaining fields stay single.
 */
export function buildVisionPocDisplayItems(
  rows: VerificationFieldRow[]
): VisionPocDisplayItem[] {
  const byField = new Map(rows.map((r) => [r.field, r]));
  const used = new Set<string>();
  const out: VisionPocDisplayItem[] = [];

  const pushPair = (def: EnArPairDef, kind: "name_pair" | "party_pair") => {
    const en = byField.get(def.en);
    const ar = byField.get(def.ar);
    if (!en && !ar) return;
    if (en) used.add(def.en);
    if (ar) used.add(def.ar);
    out.push({
      kind,
      key: `${def.en}-${def.ar}`,
      label: def.label,
      labelAr: def.labelAr,
      english: en,
      arabic: ar,
    });
  };

  pushPair(NAME_PAIR, "name_pair");
  pushPair(PARTY_ONE, "party_pair");
  pushPair(PARTY_TWO, "party_pair");

  for (const row of rows) {
    if (!used.has(row.field)) {
      out.push({ kind: "single", row });
    }
  }

  return out;
}
