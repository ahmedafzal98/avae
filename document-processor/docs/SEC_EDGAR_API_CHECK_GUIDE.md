# SEC EDGAR API — Check & Details Guide

How to verify the SEC EDGAR API is working and understand its structure.

---

## 1. API Overview

| Property | Value |
|----------|-------|
| **Base URL** | `https://data.sec.gov` |
| **Auth** | None required |
| **Format** | JSON |
| **Rate limit** | ~10 requests/second (User-Agent required) |
| **Docs** | [SEC EDGAR APIs](https://www.sec.gov/edgar/sec-api-documentation) |

---

## 2. Key Endpoints

### Company Facts (XBRL financial data)

Returns all XBRL concepts for a company in one call.

```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
```

**Example:** Apple Inc. (CIK 320193)

```
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
```

### Submissions (filing history)

Returns company metadata and filing history.

```
GET https://data.sec.gov/submissions/CIK{cik}.json
```

**Example:**

```
https://data.sec.gov/submissions/CIK0000320193.json
```

---

## 3. cURL Commands (with User-Agent)

The SEC requires a `User-Agent` header that identifies your application.

### Company Facts (Apple)

```bash
curl -H "User-Agent: AVAE Document Processor (compliance@example.com)" \
  -H "Accept: application/json" \
  "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
```

### Submissions (Apple)

```bash
curl -H "User-Agent: AVAE Document Processor (compliance@example.com)" \
  -H "Accept: application/json" \
  "https://data.sec.gov/submissions/CIK0000320193.json"
```

### Test from your machine

```bash
# Quick test - should return JSON (first 500 chars)
curl -s -H "User-Agent: AVAE Test (test@example.com)" \
  "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json" | head -c 500
```

**Expected:** JSON starting with `{"cik":"0000320193","entityName":"APPLE INC.",...`

**If 403:** User-Agent missing or blocked.

**If timeout:** Network/firewall blocking `data.sec.gov`.

---

## 4. Python Test (using your client)

```bash
cd document-processor
python3 -c "
from app.clients.sec_edgar import fetch_company_facts

# Apple Inc. CIK
result = fetch_company_facts('320193')
if result:
    print('✅ SEC API OK')
    print('Company:', result.get('company_name'))
    print('CIK:', result.get('cik'))
    print('Revenue:', result.get('revenue'))
    print('Net Income:', result.get('net_income'))
    print('Total Assets:', result.get('total_assets'))
else:
    print('❌ SEC API failed')
"
```

---

## 5. Sample CIKs for Testing

| Company | CIK | Ticker |
|---------|-----|--------|
| Apple Inc. | 0000320193 | AAPL |
| Microsoft | 0000789019 | MSFT |
| Amazon | 0001018724 | AMZN |
| Alphabet (Google) | 0001652044 | GOOGL |
| Tesla | 0001318605 | TSLA |

---

## 6. Company Facts JSON Structure

The Company Facts response has this shape:

```json
{
  "cik": "0000320193",
  "entityName": "APPLE INC.",
  "facts": {
    "us-gaap": {
      "Revenues": {
        "label": "Revenues",
        "description": "...",
        "units": {
          "USD": [
            {
              "end": "2025-09-27",
              "val": 383285000000,
              "form": "10-K",
              "fy": 2025,
              "fp": "FY"
            }
          ]
        }
      },
      "NetIncomeLoss": { ... },
      "Assets": { ... },
      "EarningsPerShareDiluted": { ... }
    }
  }
}
```

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| **403 Forbidden** | Missing/invalid User-Agent | Add `User-Agent: YourApp (contact@example.com)` |
| **429 Too Many Requests** | Rate limit | Wait; stay under 10 req/sec |
| **404 Not Found** | Invalid CIK | Use 10-digit CIK (e.g. 0000320193) |
| **Timeout** | Network/firewall | Check if `data.sec.gov` is reachable |
| **Connection refused** | Proxy/VPN | Try without proxy or different network |

---

## 8. SEC Developer Policy

- Identify your application in the User-Agent
- Do not exceed 10 requests per second
- [SEC Developer FAQs](https://www.sec.gov/os/webmaster-faq#developers)
