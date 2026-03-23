# AVAE Loom Video Script — UK Business Owners & CTOs

**Agentic Verification and Audit Engine**  
Single, high-quality, mass-distributable video for UK market

---

## Strategic Overview

| Element | Decision |
|--------|----------|
| **Format** | One generic video (90–120 sec), no per-client customisation |
| **Audience** | UK business owners, CTOs, compliance leads |
| **Tone** | Professional, understated, evidence-based — British business style |
| **Core message** | "AI that doesn't hallucinate. Verification against official UK sources." |
| **Industry problem** | Manual compliance verification is slow, expensive, and error-prone; generic AI tools invent data. |

---

## The Industry Problem to Highlight

**Primary pain (lead with this):**

> "When you're verifying documents against Companies House, EPC registers, or Land Registry, you're either doing it manually — which costs hours per document — or you're using AI tools that *hallucinate*. They'll confidently tell you a company number matches when it doesn't. That's not acceptable for compliance."

**Secondary pain:**

> "Regulators and auditors want proof. Not 'the AI said so' — they want a clear audit trail showing exactly what was extracted, what the official source returned, and whether it matched. That's what AVAE delivers."

**UK-specific angle:**

> "We built this for UK compliance. Companies House, HM Land Registry, EPC Open Data — the official sources your teams already trust. We're not replacing your process; we're making it verifiable and scalable."

---

## Video Structure: Phases & Timestamps

| Phase | Duration | Purpose |
|-------|----------|---------|
| 1. Hook | 0:00–0:12 | Establish credibility, state the problem |
| 2. The Problem | 0:12–0:28 | Deepen pain, UK compliance context |
| 3. The Solution | 0:28–0:45 | AVAE value prop, zero-hallucination |
| 4. Demo: Upload & Verification | 0:45–1:25 | Show the engine in action |
| 5. Demo: Audit Trail & HITL | 1:25–1:50 | Enterprise trust, human-in-the-loop |
| 6. Close & CTA | 1:50–2:10 | Soft close, next step |

**Total: ~2 minutes 10 seconds**

---

## Section-by-Section Script

### Phase 1: Hook (0:00–0:12)

**Screen:** Clean view — AVAE logo or dashboard home. No clutter.

**What to say:**

> "If you're a UK business owner or CTO dealing with compliance — KYC, property verification, EPC checks — you know the problem. Manual verification is slow. AI tools are fast but unreliable. They hallucinate. AVAE fixes that."

**Delivery notes:**
- Direct eye contact if on camera
- Slightly slower pace; pause after "they hallucinate"
- Confident, not salesy — state a fact they already feel

---

### Phase 2: The Problem (0:12–0:28)

**Screen:** Stay on clean dashboard or switch to a simple slide/diagram: "Manual vs AI — the gap."

**What to say:**

> "When you verify a company document against Companies House, or a property against Land Registry, you're either paying someone to cross-check every field by hand, or you're trusting an AI that might be wrong. Regulators don't accept 'the model said so.' They want evidence. Document value, API value, match or mismatch. That's the gap AVAE fills."

**Delivery notes:**
- Emphasise "evidence" and "match or mismatch"
- UK audience values understatement — avoid hype words like "revolutionary"

---

### Phase 3: The Solution (0:28–0:45)

**Screen:** High-level architecture or value prop slide: "Extract → Verify → Audit"

**What to say:**

> "AVAE is an Agentic Verification and Audit Engine. You upload a document — a company certificate, an EPC, a title deed. We extract structured data using AI, then we verify every field against the official source. Companies House API, Land Registry, EPC Open Data. Deterministic comparison. No hallucination. If there's a mismatch, we flag it for human review. Full audit trail, every time."

**Delivery notes:**
- "Deterministic" and "no hallucination" — say these clearly
- "Human review" — reassures risk-averse UK buyers

---

### Phase 4: Demo — Upload & Verification (0:45–1:25)

**Screen:** Live app — Upload page with Audit Target selector.

**What to show:**

| Timestamp | Action | What to say |
|-----------|--------|-------------|
| 0:45 | Show Upload page, Audit Target dropdown | "Here's the flow. You select your audit target — Companies House, Land Registry, or EPC." |
| 0:52 | Drag-and-drop or select a sample PDF | "Upload your document." |
| 0:58 | Show Live Engine Status (Extracting → Querying → Verifying) | "The engine extracts the data, fetches ground truth from the official API, and runs a deterministic comparison." |
| 1:08 | Show verification result — VERIFIED or DISCREPANCY | "You get a clear result. Green for verified, red for discrepancy. No grey area." |
| 1:15 | Point to Document Value vs API Value columns | "Document value, API value, status. Exactly what auditors expect." |

**Fallback if verification UI not ready:**
- Show API docs (`/documents/{id}/verification`) or a mockup
- Say: "Under the hood, every field is compared. I can show you the API response if you'd like — it's all there."

---

### Phase 5: Demo — Audit Trail & HITL (1:25–1:50)

**Screen:** Audit Log or HITL dashboard (or mockup).

**What to show:**

| Timestamp | Action | What to say |
|-----------|--------|-------------|
| 1:25 | Show Audit Log with status filters | "Every verification is logged. You can filter by status — verified, discrepancy, pending review." |
| 1:32 | Show HITL flow (Override, Manual Correction, Request Client Remediation) | "When there's a discrepancy, your team decides. Override with justification, correct the value, or request the client to fix the source document. Human-in-the-loop. No autonomous decisions." |
| 1:42 | Point to justification ledger or audit trail | "Full provenance. Who did what, when. Built for compliance." |

**Fallback if HITL UI not ready:**
- Show audit_logs table or API response
- Emphasise: "Every decision is logged. Override, correction, or remediation — all with full audit trail."

---

### Phase 6: Close & CTA (1:50–2:10)

**Screen:** Return to clean dashboard or your face (if on camera).

**What to say:**

> "That's AVAE. Zero hallucination. Verification against official UK sources. Full audit trail. If you'd like to see a live demo tailored to your use case — whether it's KYC, property, or EPC — the link is in the description. I'd be happy to walk you through it. Thanks for watching."

**Delivery notes:**
- "Tailored to your use case" — invites conversation without promising custom builds
- "Link in the description" — Calendly, email, or demo request form
- Warm but professional sign-off

---

## What to Show on Screen — Checklist

| Section | Must show | Nice to have |
|---------|-----------|--------------|
| Hook | AVAE branding / dashboard | — |
| Problem | Simple diagram or slide | — |
| Solution | Architecture / value prop | — |
| Demo 1 | Upload, Audit Target, Live Status, Verification result | Document vs API value table |
| Demo 2 | Audit Log, HITL options | Justification ledger, Similar Overrides |
| CTA | Clean frame, you on camera | — |

---

## Features to Demonstrate (Priority Order)

1. **Audit Target selector** — EPC, Companies House, HM Land Registry
2. **Upload flow** — drag-and-drop, file accepted
3. **Live Engine Status** — Extracting → Querying → Verifying (or equivalent stages)
4. **Verification result** — VERIFIED / DISCREPANCY_FLAG with field-level comparison
5. **Audit Log** — filterable by status
6. **HITL actions** — Override, Manual Correction, Request Client Remediation (if UI exists)

---

## Ending & CTA Structure

**CTA options (pick one for description):**

- **Option A (soft):** "Book a 15-minute demo" — Calendly link
- **Option B (direct):** "Reply to this email with 'Demo' and I'll send a personalised walkthrough"
- **Option C (technical):** "Request API access for a proof-of-concept" — for CTOs

**Video description template:**

```
AVAE — Agentic Verification and Audit Engine
Zero hallucination • UK compliance • Companies House, Land Registry, EPC

[1–2 sentence value prop]

🔗 Book a demo: [Calendly URL]
📧 Questions: [email]
```

---

## Pitfalls to Avoid

| Pitfall | Why it matters | Mitigation |
|---------|----------------|------------|
| **Over-claiming** | UK buyers are sceptical; "revolutionary" and "game-changing" backfire | Use "verifiable," "deterministic," "audit trail" |
| **US-centric examples** | SEC, IRS — not relevant to UK audience | Stick to Companies House, Land Registry, EPC |
| **Ignoring GDPR / data residency** | UK enterprises care where data lives | Mention "UK data residency" or "EU-compliant" if true |
| **Rushing the demo** | CTOs want to see it work | Pause on verification result; let them read the columns |
| **Generic AI pitch** | "AI-powered" is table stakes; differentiator is verification | Lead with "zero hallucination" and "official sources" |
| **No human-in-the-loop** | Risk-averse buyers fear autonomous AI | Explicitly say "human decides" on discrepancies |
| **Too long** | Busy execs drop off after 2 min | Keep under 2:15; trim Problem section if needed |
| **Per-client customisation** | You said you want one video | Use "tailored to your use case" in CTA, not "custom build" |

---

## UK Market — Best Recommendations for Closing Deals

| Recommendation | Rationale |
|----------------|-----------|
| **Lead with compliance, not speed** | UK buyers prioritise risk reduction over efficiency gains |
| **Offer a pilot, not a big contract** | "Let's run 50 documents through AVAE and compare to your current process" — low commitment |
| **Provide a written security/compliance summary** | One-pager on data handling, retention, audit trail — they'll ask for it |
| **Reference UK regulations** | AML, KYC, property due diligence — name the frameworks they care about |
| **Avoid hard sell** | "I'd be happy to walk you through it" beats "Book now before the offer ends" |
| **Follow up with a short email** | "Here's the link again. Happy to answer any questions." — persistence without pressure |
| **Prepare for procurement** | UK enterprises have long procurement cycles; have a standard contract and security questionnaire ready |
| **Use case-specific demos on the call** | One video is generic; the live call should show *their* document type (e.g. EPC if they're in property) |

---

## Quick Reference Card (Print or Second Screen)

```
0:00  Hook — "Manual is slow, AI hallucinates. AVAE fixes that."
0:12  Problem — "Regulators want evidence. Document vs API, match or mismatch."
0:28  Solution — "Extract, verify against official UK sources, full audit trail."
0:45  Demo — Upload, Audit Target, Live Status, Verification result
1:25  Demo — Audit Log, HITL (Override, Correction, Remediation)
1:50  Close — "Link in description. Happy to walk you through it."
2:10  End
```

---

## Pre-Recording Checklist

- [ ] App loaded at correct URL (local or deployed)
- [ ] Sample documents ready: 1× Companies House doc, 1× EPC, 1× Land Registry (or at least one)
- [ ] Audit Target selector visible and working
- [ ] Verification result screen accessible (or mockup ready)
- [ ] Browser zoom 100%, window maximised, no extra tabs
- [ ] Loom: screen + camera (optional but recommended for trust)
- [ ] Script rehearsed once; aim for natural delivery, not word-for-word

---

## Post-Recording Checklist

- [ ] Trim dead air at start/end
- [ ] Verify audio clear; no background noise
- [ ] Title: "AVAE — Document Verification for UK Compliance"
- [ ] Description: CTA link + 1–2 sentence value prop
- [ ] Thumbnail: AVAE logo or verification screenshot

---

**Ready for recording. One video, mass distribution, UK-optimised.**
