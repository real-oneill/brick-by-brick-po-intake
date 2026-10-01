# Brick-by-Brick Use Case: Intelligent Purchase Order Intake

**Program:** Brick-by-Brick @ NYU (Tech@NYU x Databricks), Fall 2026
**Industry:** Consumer Packaged Goods / Prestige Beauty (B2B order-to-cash)
**Team size:** 3 students | **Build window:** Weeks 4–10 (~8 weeks) | **Showcase:** Week 11 (in person)
**Platform:** Databricks Free Edition (serverless)
**Data:** 100% synthetic. Every company, brand, retailer, person, SKU, and price in this project is fictional.

---

## 0. How to read this document

This document tells you **what** a good solution has to do. It does not tell you **how** to build it. Choosing the approach is your job, and it's a big part of what the judges will look at. The Databricks platform gives you several ways to solve almost every step. Try things, measure them, and be ready to explain why you chose what you chose.

Your mentor will help you weigh the options but won't hand you the design.

## 1. Why this problem is real

This use case is modeled on a real engagement at a global prestige beauty company. Details are anonymized and every number below is approximate.

A single regional business unit at that company receives on the order of **100,000 retailer purchase orders a year**, and **most of them are keyed into the ERP by hand**. Customer-service reps pull orders from shared inboxes, fax queues, voicemails, and field-sales chats. They read each document, look up who the customer is and which product the retailer means, check whether stock exists, and then type the order line by line into the ERP.

The company has tried twice to fix this:

1. **Standardized order templates.** Large retailers refused to change their own systems, and small ones kept sending whatever they always had.
2. **Rules-based RPA (screen-scraping bots).** It broke every time a retailer changed a column, a logo, or a language.

The variety of formats killed both approaches. The question for your team is whether **AI + a governed data platform + a human in the loop** can succeed where templates and RPA failed.

> For the purposes of this project, the supplier is **Maison Solenne**, a fictional prestige beauty group with 8 brands, selling to 14 retail customers in 6 countries.

## 2. The problem

### 2.1 Orders arrive through every channel imaginable

| Channel | What it looks like | Example customer (fictional) |
|---|---|---|
| ERP / EDI | X12 purchase-order and change-order files, retailer's own item numbers, multiple ship-to DCs | Halcyon & Finch (US dept store) |
| Email + PDF | System-generated PDF attached to an email, items identified by barcode (GTIN) | Glow Republic (US beauty chain) |
| Fax | Low-resolution, skewed, noisy scans; French language; `12,50` decimal commas; `DD/MM/YYYY` | Pharmacie Lumen (FR pharmacy co-op) |
| Handwritten | Hand-filled order forms, photographed or scanned. Product *names* only, no codes, abbreviations and misspellings | Corso Profumerie (IT indie perfumery) |
| Excel buysheets | One workbook holding many POs (one per airport store), quantities in **cases**, mixed USD/EUR | Meridian Travel Retail (duty free) |
| Portal export | JSON / CSV with German headers (`Artikelnummer`, `Menge`), some codes already discontinued | BeautyHaus Online (DE e-tailer) |
| Email body | The order is typed into the body of the email, sometimes with an Arabic signature; prices in AED | Al Noor Trading (UAE distributor) |
| Phone | Call-center speech-to-text transcripts: "uh, actually make that twelve", spelled-out numbers | Kensington Salon Supply (UK salon distributor) |
| Price-list template | The supplier's *entire* price list sent back with quantities filled in on a few rows | Northbay Drug (US drugstore) |
| Amended scans | Typed PDFs with handwritten strike-throughs, "+2 cs", "cancel line 4", circled free goods ("FOC") | Harlow & Vale (UK dept store) |
| **Multimodal** | Image-heavy documents mixing printed text, **product photos**, stamps, badges, and handwriting (see §2.2) | 4 German perfumeries + several of the above |

### 2.2 Multimodal documents and complexity levels

Many real orders aren't "a document with a table". They're pictures: a promo flyer with product photos and quantities scrawled across it, a catalog page with items circled, or a chat screenshot that says "6 of these 👇" above a product photo. The corpus contains a **mix of four multimodal document types**:

| Type | What it is |
|---|---|
| **Promo form** | Maison Solenne's German promotional order form ("Aktionsformular"): product photos, orange discount badges, EAN/EDI codes, and fields the shop fills in by hand |
| **Catalog markup** | A trade-catalog page of product photos. The buyer circles what they want and writes "x 24" or "3 cs" next to it, with no item codes |
| **Chat screenshot** | A field-sales chat forwarded by a rep: messages, product photos, a photo of a handwritten list, and corrections |
| **Inline-image email** | An HTML email where the products appear *only* as pasted screenshots ("12 of each of these"), sometimes with a photo attached |

**Every document in the corpus carries a complexity rating from 1 to 4**, so you can report results by difficulty and decide where to start:

| Level | Meaning | Examples |
|---|---|---|
| **1 · Simple** | Clean, digital, structured | EDI, portal export, typed promo form |
| **2 · Moderate** | Clean but semi-structured, or a light scan | Excel buysheet, price-list template, email body, promo form with handwriting inside the boxes |
| **3 · Complex** | Degraded, handwritten, or spoken. Meaning must be inferred | Fax, phone, amended scans, quantities scrawled outside boxes, "+1 Tester", offers left blank |
| **4 · Extreme** | Several hard things at once | Phone photos with shadows and perspective, crossed-out corrections, sticky notes overriding the ship-to, upside-down pages, customer identified only by a shop stamp |

### 2.3 Why it's hard (the messiness is the point)

- **Identity resolution.** "Halcyon Finch NYC", "H&F Inc.", and "HALCYON & FINCH - DC 0042" are one customer. A retailer item number, a barcode, a discontinued material code, a product photo, and "Rouge Velours lipstick #12" can all mean the same SKU. About 1 in 7 retailer item numbers has no entry in the cross-reference table.
- **Conformance.** Every line has to become a single canonical shape: each vs. case (case packs vary by SKU), decimal commas, several date formats, four currencies, free-of-charge lines, testers, and promotional discounts.
- **Business rules that only live in people's heads ("tribal knowledge").** Examples: "When Corso doesn't give a size, they mean the 100 ml." "Meridian's quantities are cases." "DC 0042 closed in September, so reroute to 0047." "Promo-form price = EK minus the badge discount."
- **Inventory reality.** An order is only good if it can be fulfilled. About 10–15% of lines are short or out of stock, which forces a decision: ship partial, backorder, or substitute the successor SKU.
- **Duplicates and amendments.** The same PO can arrive by email *and* by fax. A later document can cancel or change lines on an earlier PO.
- **Trust.** A wrong order can mean a $40K shipment to the wrong DC or a missed holiday launch. The business won't accept "the AI said so". Every automated decision has to be explainable, reviewable, and auditable.

### 2.4 Stakeholders

| Stakeholder | What they care about |
|---|---|
| Customer-service order-entry reps | Fewer keystrokes. A review screen they trust. Clear reasons for *why* an order needs them |
| CS team lead | Throughput, backlog, SLA (order in ERP within X hours of receipt) |
| Supply chain / demand planning | Allocation of scarce inventory, backorder visibility |
| Key account managers (Sales) | Retailer relationships; nothing embarrassing reaches the customer |
| Finance | Price accuracy vs. the contracted price list and promotions; free goods tracked correctly |
| IT / ERP team | A clean, well-defined outbound order interface. No new systems to babysit |
| Data governance / internal audit | Who saw what, who changed what, which model and prompt version made each decision |

## 3. What your team will build

An end-to-end, governed solution **on Databricks, using its data and AI capabilities**, that turns this pile of documents into **synthesized, ERP-ready sales orders**, with a human reviewing anything the system isn't confident about. The data must flow through a **medallion architecture** (raw → refined → business-ready).

```
 Channels (11)          BRONZE (raw)            SILVER (refined)                 GOLD (business-ready)        People / ERP
 ─────────────          ────────────            ────────────────                 ─────────────────────        ────────────
 EDI · email · fax  ──► every inbound file, ──► machine-readable content   ──►  proposed sales orders     ──► interactive review app
 handwritten · Excel    as received, with       per document; extracted         (customer + SKU resolved,     (approve / edit / reject)
 portal · phone ·       arrival metadata        headers + lines in a typed      inventory + price checked,          │
 price list · scans ·                           schema; conformed units,        confidence + reasons)               ▼
 multimodal                                     dates, currencies, IDs          accuracy + ops metrics       approved orders ──► mock ERP
                                                                                                             corrections ──► evaluation set
  Master data: products · customers · ship-tos · retailer item cross-reference · price list · inventory (ATP) · retailer rules
  Across everything: access control on every asset · lineage · versioned prompts & models · traced AI calls · audit trail · packaged & CI/CD-ready
```

### 3.1 Provided to the team

A synthetic corpus, in the `data/` folder of the course repo ([github.com/real-oneill/brick-by-brick-po-intake](https://github.com/real-oneill/brick-by-brick-po-intake)), containing:

- **184 training documents** (220 POs, ~2,700 order lines) across 11 channels and 9 file types: PDF, PNG, JPG, EML, XLSX, CSV, JSON, X12 `.edi`, and TXT transcripts. That includes **24 multimodal documents** across all four multimodal types and all four complexity levels.
- **48 holdout documents** (58 POs, ~940 lines). Held back by the mentor and released only for the **Week 11 showcase evaluation**, so teams can't overfit.
- **Master data** as CSVs: product master (163 SKUs across 8 brands, with case packs, barcodes, testers, and discontinued → successor links), 14 customers and their ship-tos (with name variants), retailer item cross-reference (deliberately incomplete), contracted price list, inventory / available-to-promise, and 17 retailer rules written in plain English.
- **Ground truth** for the training set: expected headers, expected lines (including the expected inventory outcome per line), a complexity rating per document, and a labeled list of every injected issue across 35 issue types. `data/README.md` documents every file and column.

## 4. Requirements

Requirement IDs are referenced in the scope tiers (§5) and the showcase rubric (§8). Each one says what must be true, not which feature to use.

### 4.1 Ingestion (BRONZE)

| ID | Requirement |
|---|---|
| ING-1 | Land every channel's files in **governed storage on Databricks**. Simulate arrival by uploading in batches, not all at once. |
| ING-2 | Ingest **incrementally and idempotently**. New files are picked up automatically, and re-running never duplicates rows. |
| ING-3 | Bronze keeps the **original document** plus arrival metadata: channel, filename, received timestamp, sender, subject, content hash. Nothing gets thrown away. |
| ING-4 | Detect the exact same file arriving twice, at ingest. |

### 4.2 Understanding documents & extraction (SILVER)

| ID | Requirement |
|---|---|
| PAR-1 | Turn every document, whether typed, scanned, faxed, photographed, handwritten, image-heavy, spoken, or structured, into **machine-readable content** that downstream steps can use. Record a measure of how confident you are in it. |
| PAR-2 | Handle each format in the way that is **most reliable and cost-effective for that format**. Be ready to justify, per format, why your approach is the right one. |
| PAR-3 | **Multimodal:** when the meaning lives in an image (a product photo, a circled item, a badge, a stamp, a sticky note), your pipeline must still capture it, or route it to a human with a clear reason. |
| EXT-1 | Extract header and line items into a **typed schema**. The schema must support **multiple POs per document**, amendments (change / cancel / add), free goods, and testers. |
| EXT-2 | Every extracted header and line carries a **confidence score** and a pointer back to its source (page / region / row / message) so a reviewer can verify it. |
| EXT-3 | Large documents (up to ~190 lines across 5 pages or 5 sheets) must be fully extracted. A failed or truncated extraction must be visible as **FAILED**, never as an empty "success". |
| EXT-4 | Detect **duplicates** (same PO via two channels) and **amendments/cancellations** of an earlier PO. |

### 4.3 Conformance, resolution & business rules (SILVER → GOLD)

| ID | Requirement |
|---|---|
| CON-1 | Conform every line to canonical units (eaches), ISO dates, ISO currency, and numeric decimals. |
| RES-1 | Resolve the **customer** (sold-to and ship-to) from name variants, addresses, DC codes, handwritten customer numbers, or shop stamps. |
| RES-2 | Resolve the **SKU** from whatever the document gives you: retailer item number, barcode, material code (including discontinued → successor), description, or picture. Every match records how it was made and its confidence. |
| RUL-1 | Apply the retailer rules (§2.3 and `retailer_rules.md`). Rules must be **maintainable by the business** and auditable, not buried in scattered code. |
| ATP-1 | Check each line against **inventory / available-to-promise** and propose an outcome: FULL, PARTIAL, BACKORDER, or SUBSTITUTE (successor SKU), with the reason. |
| PRC-1 | Compare the document price with the **contracted price** (or the promotion's net price). Flag mismatches above a tolerance. Free goods and testers are priced 0. |
| GLD-1 | Produce proposed sales orders (header + lines) with an overall confidence, a needs-review flag, and **human-readable review reasons**. |

### 4.4 Human in the loop (interactive QC/QA)

| ID | Requirement |
|---|---|
| HIL-1 | An **interactive application, hosted on Databricks**, where a reviewer works a queue of orders sorted by risk (lowest confidence and highest value first). |
| HIL-2 | A side-by-side view: the original document (PDF / image / transcript / chat) next to the extracted, editable header and lines, with the low-confidence fields highlighted. |
| HIL-3 | Reviewers can approve, edit, reject, pick from suggested SKU matches, and accept or override inventory decisions. |
| HIL-4 | Every reviewer action is recorded in an **append-only audit trail** with: who, when, before → after, and the reason. |
| HIL-5 | Approved orders flow to an approved-orders table and a **mock ERP outbound** (e.g. a JSON order payload). |
| HIL-6 | Corrections feed back. Fixed SKU matches can enrich the cross-reference (with approval), and corrected documents join the evaluation set. |

### 4.5 AI quality, accuracy logging & tracing

| ID | Requirement |
|---|---|
| ACC-1 | Measure accuracy against ground truth **per field, per channel, and per complexity level**: header fields, line-level SKU, quantity, price, customer, and inventory outcome. |
| ACC-2 | **Log every pipeline and evaluation run** (metrics, parameters, prompt version, model version) so accuracy over time is a chart, not an opinion. |
| ACC-3 | **Trace every AI call**, so any extracted value can be traced to the exact prompt, input, model, and output. |
| ACC-4 | Report the **straight-through-processing (STP) rate** (orders needing no human touch) together with the **false-confidence rate** (orders marked confident that were actually wrong). The second number matters more. |
| ACC-5 | A **dashboard** for the CS team lead: volume by channel and complexity, STP rate, review backlog, accuracy trend, top review reasons, and inventory shortfalls. |

### 4.6 Packaging & CI/CD plan

You **don't** have to build a CI/CD pipeline or actually promote anything from dev to prod. You **do** have to package the solution so it *could* be promoted, and explain exactly how it would be.

**Packaging (built)**

| ID | Requirement |
|---|---|
| PKG-1 | **Everything is code in a Git repo**: pipelines, jobs, the app, dashboards, prompts, setup scripts. Someone else could recreate your solution from the repo alone. No click-ops resources in the final demo. |
| PKG-2 | **Nothing environment-specific is hard-coded**: catalog/schema names, workspace URLs, model endpoints, secrets. Configuration is parameterized, so the same code could run unchanged in dev, test, or prod. |
| PKG-3 | **Prompts are versioned, governed assets**, loaded by version or alias at runtime. You can always say which prompt version produced which output. |
| PKG-4 | **Models are versioned, governed assets**, including any model you train or fine-tune. |
| PKG-5 | **Unit tests** cover your deterministic logic (UOM conversion, date parsing, SKU matching, rules) and run with one command. |

**CI/CD plan (written, not built).** About 2 pages plus one diagram, in the repo, and summarized in under 2 minutes at the showcase.

| ID | The plan must explain |
|---|---|
| PLAN-1 | **Environments:** which ones you'd have (e.g. dev / test / prod), how they'd be isolated (workspaces, data, identities), and what data each one uses. |
| PLAN-2 | **Pipeline stages:** what happens automatically on a pull request, on merge, and on a release (tests, validation, deployment, approvals), and which tools would run each step. |
| PLAN-3 | **Promoting AI assets:** how a new prompt or model version gets from an experiment to prod, including the **evaluation gate**: it must beat the current version on ground truth, with no regression in false confidence. |
| PLAN-4 | **Identities & secrets:** what identity deploys to prod (not a person's account), how secrets are handled, and who approves a prod release. |
| PLAN-5 | **Rollback & monitoring:** how you'd roll back a bad release or a bad prompt, and what you'd watch after a deployment (accuracy drift, STP rate, false confidence, cost). |

### 4.7 Governance, access control & auditability

| ID | Requirement |
|---|---|
| GOV-1 | **Every** asset is governed with explicit, least-privilege access: data, files, functions, models, prompts, the app, and dashboards. |
| GOV-2 | Define at least three personas and grant least privilege: **pipeline engineers** (build), **CS reviewers** (read the queue, write corrections only through the app), **auditors** (read-only on audit + lineage). |
| GOV-3 | Sensitive fields (buyer contact details, contracted prices) are protected, e.g. reviewers only see prices for their region. |
| GOV-4 | The app runs with its own least-privilege identity, and reviewer actions are attributed to the **human user**. |
| GOV-5 | **Lineage** shows, end to end, how any approved order line traces back to its raw document. Assets carry descriptions and tags. |
| GOV-6 | You can answer the auditor's question live: *"For approved order X, line 3: what document did it come from, which prompt and model version extracted it, what was the confidence, and who approved or changed it?"* |

### 4.8 Non-functional

- **Cost-aware:** Free Edition has quotas, and AI document processing is usually priced per page or per token. Develop on a small sample, run the full corpus deliberately, and report an approximate **cost or compute per document**, by complexity level.
- **Idempotent and re-runnable:** a full refresh reproduces the same gold tables.
- **No real data, ever.** Synthetic corpus only.

## 5. Scope tiers (find your way in)

The team doesn't have to do everything. Tier 1 is a complete, demo-able project on its own.

| Tier | Goal | Requirements |
|---|---|---|
| **Tier 1: Foundation** (must) | Complexity-1 and -2 documents end to end (at least EDI, Email/PDF, and Excel). Bronze → Silver → Gold with customer + SKU resolution via cross-reference. A basic review app (approve/edit). Everything in Git. Accuracy computed against ground truth. | ING-1–3, PAR-1–2, EXT-1–2, CON-1, RES-1, RES-2 (exact matches), GLD-1, HIL-1–3, ACC-1, PKG-1, GOV-1 |
| **Tier 2: Production-shaped** (target) | All channels including fax, handwriting, phone, and complexity-3 multimodal documents. Inventory and price checks. Confidence-based routing. Versioned prompts, traced AI calls, logged evals. Parameterized, tested repo + a written CI/CD plan. Personas + least privilege + protected fields. Audit trail. Dashboard. | + ING-4, PAR-3, EXT-3, RUL-1, ATP-1, PRC-1, HIL-4–5, ACC-2–5, PKG-2–3, PKG-5, PLAN-1–5, GOV-2–6 |
| **Tier 3: Stretch** (impress the judges) | Complexity-4 documents. Duplicate/amendment detection. Image- or meaning-based SKU matching as a versioned model. A feedback loop from corrections. An automated evaluation you could use as the promotion gate. Automated quality judges. Natural-language Q&A for the CS lead ("what's stuck and why?"). | + EXT-4, RES-2 (fuzzy/semantic/visual), HIL-6, PKG-4 |

## 6. Suggested week-by-week plan

Weekly in-class platform topics are set by the Instructors. This is a *suggested* sequence of project milestones; adjust it with your Mentor.

| Week | Milestone | Done when… |
|---|---|---|
| 4 | **Explore & land.** Set up Free Edition and a Git repo. Explore the corpus and master data. Run quick experiments on how the platform can read a fax, a handwritten form, and a promo form. | Master data queryable; a short write-up of what you tried on 3 hard documents and what worked |
| 5 | **Bronze.** Incremental, idempotent ingestion of every channel. | Re-running doesn't duplicate; all channels landed |
| 6 | **Understand + extract.** Machine-readable content for every format; first extraction into your schema; first versioned prompt. | Extracted orders for complexity-1/2 documents; first accuracy number |
| 7 | **Resolve, conform, inventory.** Customer and SKU resolution, conformance, inventory and price checks, proposed sales orders. | Gold orders with confidence + review reasons |
| 8 | **Human in the loop.** Review app and audit trail. | A reviewer can fix and approve an order; audit row written |
| 9 | **Govern & package.** Personas and access control, tracing, an evaluation run, parameterized config, unit tests, dashboard. Write the CI/CD plan. | CI/CD plan reviewed with your mentor |
| 10 | **Harden + rough-draft presentation.** Run the full corpus, fix the worst failure categories (by complexity level), rehearse. | Draft deck + live demo path |
| 11 | **Showcase.** The mentor releases the holdout set the week before. Teams run it and report honest numbers. | Final presentation |

## 7. Definition of "good" (target metrics on the holdout set)

These are stretch-realistic targets, not pass/fail lines. Showing honest numbers and the failure analysis behind them beats inflated ones. **Report every metric by complexity level.** Nobody expects level 4 to match level 1.

| Metric | Target |
|---|---|
| Header accuracy (PO#, sold-to, ship-to, dates, currency) | ≥ 95% |
| Line-level SKU (material) accuracy | ≥ 90% |
| Quantity accuracy (after UOM conversion) | ≥ 97% |
| Straight-through-processing rate | ≥ 50% of orders |
| **False-confidence rate** (wrong but not sent to review) | **≤ 2%** |
| Every approved line traceable to document + prompt version + reviewer | 100% |

## 8. Week 11 showcase rubric (judges)

| Criterion | Weight | What "ship-ready" looks like |
|---|---|---|
| **Business outcome** | 20% | The team frames the problem the way the CS lead would. Reports STP rate, accuracy (by complexity), and time saved honestly on the holdout set. |
| **Handling the mess** | 20% | Handwritten, fax, phone, multimodal, multi-PO, discontinued SKUs, and stock shortfalls are handled or routed to a human *with a clear reason*. |
| **Human-in-the-loop experience** | 20% | A reviewer could use the app on Monday. It's fast and explains why each order is in the queue. Corrections stick. |
| **Governance & auditability** | 20% | Live answer to the auditor question (GOV-6). Least-privilege personas. Prompts and models are versioned and traced. |
| **Engineering & design choices** | 20% | A clean, parameterized, tested repo, idempotent pipelines, and a credible CI/CD plan (environments, gates, identities, rollback). **The team can explain why each design choice beat the alternatives they tried.** |

## 9. Real-world trade-offs to discuss with your advisor

- **Automation vs. trust.** Every point of STP you gain by lowering the review threshold can cost you in false confidence. Where would *you* set it, and why?
- **One big prompt vs. many small steps.** A single "extract everything" call is fast to build but hard to debug and evaluate. A staged pipeline is the opposite.
- **Cost per page.** AI document processing is often priced per page or per token. A 12-page buysheet costs 12× a one-pager. Is it ever worth sending a spreadsheet through it?
- **Pictures vs. text.** When a product is only shown as a photo, do you trust the model's read of the image, match the photo against your catalog, or always ask a human?
- **Rules as data vs. rules in the prompt.** "Meridian = cases" could live in a lookup table, in the prompt, or both. Which is easier to audit and to change?
- **Inventory allocation.** If two retailers want the last 50 units, who gets them? The extraction is the easy part; the business decision isn't.
- **Feedback loops.** Auto-adding every reviewer correction to the cross-reference table is fast but risky. Who approves changes to master data?

## 10. Free Edition notes & known constraints

- **Serverless only.** One 2X-Small SQL warehouse, up to 3 apps (they auto-stop after 24h), one managed Postgres project, one active pipeline per pipeline type, and limited model-serving endpoints (no GPU, no provisioned throughput). Design within these limits.
- **One workspace.** You won't promote between environments, but your CI/CD plan should say how you'd isolate them at a real company (typically separate workspaces) and how the same code would run in each.
- **Verify early (Week 4)** that the platform capabilities your design depends on are available on Free Edition. If something isn't, talk to your mentor about alternatives.
- **Free Edition is non-commercial.** This is a learning project.

## 11. Contacts

- **Industry Advisor:** *(name / role / Slack)*
- **Mentor (Databricks SA):** Evan O'Neill
- **Program organizers:** see the program Slack channel
