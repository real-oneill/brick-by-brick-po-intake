# Maison Solenne PO Intake Corpus (synthetic)

The synthetic dataset for the Brick-by-Brick @ NYU use case *Intelligent Purchase Order Intake*. **Everything here is fictional.** Every company, brand, retailer, person, product, GTIN, address, and price is invented. GTINs use the GS1 `29` prefix, which is reserved for internal use, so none of them collide with real products.

| | train | holdout |
|---|---|---|
| Documents | 184 | 48 |
| …of which multimodal | 24 | 8 |
| Purchase orders (some docs contain several) | 220 | 58 |
| Order lines | 2,719 | 943 |
| Complexity 1 / 2 / 3 / 4 | 43 / 43 / 74 / 24 | 10 / 11 / 22 / 5 |
| Size | 26 MB | 9 MB |

> **The holdout set is for the Week 11 showcase.** Your mentor releases the 48 holdout documents (without answers) the week before the showcase. You run them through your solution, and they're scored against a private answer key.

## Layout

```
master_data/                 reference data your pipeline joins against
documents/<split>/<channel>/DOC-xxxxx.<ext>   raw inbound documents, one folder per channel
documents/<split>/_arrivals.csv               what the inbox / EDI gateway knows on arrival (no answers)
ground_truth/<split>/        the answer key: manifest, headers, lines, issues
```

Suggested Unity Catalog layout: upload each channel folder to `/Volumes/<catalog>/po_intake/landing/<channel>/` in batches to simulate arrival, and load `master_data/*.csv` as Delta tables.

## The 11 channels

| Channel folder | Retailer (fictional) | Formats | What makes it hard |
|---|---|---|---|
| `erp_edi` | Halcyon & Finch (US dept store) | `.edi` X12 850 and **860 (change orders)** | Retailer's own 8-digit item numbers (`IN`), some without a cross-reference. GTIN (`EN`) only sometimes. Cases (`CA`) vs eaches. Closed DC 0042. Multi-PO interchanges |
| `email_pdf` | Glow Republic (US beauty chain) | `.eml` with a PDF attachment | Unpack the attachment first. Items by GTIN, some discontinued. "PROMO - NO CHARGE" free goods. Up to ~95-line multi-page POs |
| `fax` | Pharmacie Lumen (FR); also **Glow Republic duplicates** | `.pdf` (image) / `.png` | 150 dpi, binarized, skewed, speckled. French. Decimal commas, DD/MM/YYYY. Some POs were already emailed (duplicates). Garbled PO numbers (`O` vs `0`) |
| `handwritten` | Corso Profumerie (IT perfumery) | `.jpg` phone photos / `.pdf` scans | Handwriting. Product **names only**, abbreviated and misspelled. Size often omitted (rule R03). PO number sometimes missing |
| `excel_buysheet` | Meridian Travel Retail (duty free) | `.xlsx` | **One PO per sheet** (2–5 airport stores). Quantities in **cases**. USD and EUR. Header block above the table, formula totals, hidden blank rows |
| `portal_export` | BeautyHaus Online (DE e-tailer) | `.json` / `.csv` (`;`-delimited) | German field names, decimal commas, DD.MM.YYYY. Often superseded material codes (rule R08) |
| `email_body` | Al Noor Trading (UAE distributor) | `.eml` | The order is **free text in the email body**, sometimes with an Arabic signature. AED. Prices sometimes omitted. Amendment emails. A later "formal copy" PDF duplicates an earlier body order |
| `phone` | Kensington Salon Supply (UK) | `.txt` / `.json` ASR transcripts | Speech-to-text: spelled-out numbers, "uh, actually make that thirty" corrections, misheard names ("hydro repair"). Salon-size default (R07). JSON has per-segment ASR confidence |
| `email_pricelist` | Northbay Drug (US drugstore) | `.eml` with an `.xlsx` attachment | They return the **entire** price list (~140 rows) and only 5–15 rows have quantity > 0 (rule R06) |
| `amended_scan` | Harlow & Vale (UK dept store) | `.pdf` (image) | Typed PO with **handwritten amendments**: struck-through "cancel" lines, "+2 cs" quantity changes, circled "FOC" free goods. Up to ~140 lines over 5 pages |
| `multimodal` | 4 German perfumeries, Harlow & Vale, Glow Republic, Corso, Kensington, Al Noor | `.pdf` / `.jpg` / `.png` / `.eml` | A **mix of image-heavy documents** (see below). Meaning lives in product photos, badges, stamps, circles and handwriting |

### Multimodal document types × complexity

| `doc_type` | Levels | What it is |
|---|---|---|
| `promo_form` | 1–4 | Maison Solenne German promo form ("Aktionsformular"): product photos, orange discount badges ("RR 15%"), EAN, EDI code box, red overprint. **L1** typed into the boxes · **L2** handwriting in the boxes + shop stamp · **L3** quantities scrawled outside the boxes ("24 Stück + 1 Tester"), offers left blank, crossed-out corrections · **L4** phone photos, sticky note overriding the ship-to, coffee ring, upside-down page, sometimes only a stamp identifies the customer |
| `catalog_markup` | 2–3 | Trade-catalog page of product photos. The buyer circles items and writes "x 24" / "3 cs", plus PO and ship-to at the top. L3 adds a second page, circled-then-crossed-out items, and sometimes a phone photo |
| `chat_screenshot` | 3–4 | Field-sales chat forwarded by a rep: "6 of these" under a product photo, a photo of a handwritten list, PO (or not). L4 adds corrections, a voice-note transcript, and is a photo of the phone screen |
| `email_inline` | 2–3 | HTML email where products appear only as inline screenshots ("12 of each of these"). L3 adds an attached photo of a handwritten stock-room list |

### Complexity (every document)

`manifest.csv` has a `complexity` column (1 simple · 2 moderate · 3 complex · 4 extreme), so you can report accuracy and cost **by difficulty**. Non-multimodal documents are rated by channel (e.g. EDI and portal export = 1; Excel, price list, email body = 2; fax, phone, amended scans, handwritten scans = 3) and bumped up one level for amendments, duplicates, multi-PO files, ≥ 90 lines, or handwritten phone photos.

## master_data/

| File | Rows | Columns |
|---|---|---|
| `product_master.csv` | 163 | material_id, brand, product_line, variant, category, description, size, shade, base_uom, case_pack, gtin, list_price_usd, status (`active`/`discontinued`), successor_material_id |
| `customer_master.csv` | 14 | sold_to_id, customer_name, name_variants (`\|`-delimited), country, currency (`USD\|EUR` for Meridian), payment_terms, primary_channel, region, supply_plant |
| `ship_to.csv` | 33 | ship_to_id (`<sold_to>-<location_code>`), sold_to_id, location_code, location_name, address, status (`open`/`closed`), closed_date |
| `retailer_item_xref.csv` | 285 | sold_to_id, retailer, retailer_item_id, material_id. **Deliberately ~85% complete.** |
| `price_list.csv` | 1,528 | sold_to_id, material_id, currency, net_price, valid_from, valid_to (contracted net prices) |
| `inventory_atp.csv` | 592 | plant, material_id, on_hand, allocated, atp_qty, next_receipt_date, next_receipt_qty, snapshot_date |
| `retailer_rules.csv` / `.md` | 17 | rule_id, retailer, rule_type, rule_text: plain-English "tribal knowledge" |

8 brands: Solenne Paris, Kōri Botanicals, Atelier Noor, Velour Cosmetics, Thornfield Grooming, Mistral Hair, Lune Rouge, and Ember & Oak. There are 4 currencies (USD, EUR, GBP, AED) and 4 supply plants (US-NJ, EU-FR, UK-MK, AE-JA).

## ground_truth/<split>/

**`manifest.csv`**: doc_id, relative_path, split, channel, retailer, file_format, received_at, sender, subject, page_count (pages, or sheets for `.xlsx`), po_count, line_count, doc_type, complexity (1–4)

**`headers.csv`** (one row per PO): doc_id, po_number (the *intended* number; blank if none was given), customer_name_as_written, sold_to_id, ship_to_as_written, ship_to_id (**after** applying reroute rules), order_date, requested_delivery_date (as stated, ISO), currency, order_type (`STANDARD`/`AMENDMENT`), is_duplicate_of (doc_id of the first copy), amends_po

**`lines.csv`**: doc_id, po_number, line_no, line_action (`ORDER`/`CHANGE`/`CANCEL`/`ADD`), raw_item_text, item_code_shown, material_id (or `UNRESOLVABLE`), substitute_material_id, qty_as_written, uom_as_written, qty_each (after UOM conversion and amendments), price_on_document (blank if not stated), expected_net_price (contract price; 0 for free goods), currency, is_free_goods, expected_atp_outcome (`FULL`/`PARTIAL`/`BACKORDER`/`SUBSTITUTE`/`N/A`), expected_ship_qty

ATP convention: each line is checked **independently** against the snapshot in `inventory_atp.csv` at the retailer's supply plant (no cross-order allocation; that's a Tier 3 stretch).
- **FULL**: `atp_qty ≥ qty`
- **PARTIAL**: `0 < atp_qty < qty`, so ship `atp_qty`
- **BACKORDER**: `atp_qty = 0`
- **SUBSTITUTE**: the material is discontinued and its successor has enough ATP

Cancelled and unresolvable lines are `N/A`.

**`issues.csv`**: doc_id, issue_type, detail. This labels every injected problem so you can measure accuracy *per problem type*.

### Issue taxonomy (train counts)

| issue_type | count | | issue_type | count |
|---|---|---|---|---|
| out_of_stock | 249 | | photo_of_handwritten_list | 7 |
| xref_missing_but_resolvable | 187 | | garbled_po_number | 6 |
| unresolvable_sku | 95 | | handwritten_customer_number | 6 |
| price_mismatch | 85 | | identify_by_image_caption | 6 |
| discontinued_sku_successor | 79 | | circled_then_crossed_out | 6 |
| uom_cases | 75 | | tester_free_goods | 5 |
| customer_name_variant | 69 | | identify_by_photo | 5 |
| free_goods | 30 | | inline_images_only | 5 |
| past_or_weekend_delivery_date | 24 | | amendment | 5 |
| handwritten_amendment | 24 | | duplicate_submission | 5 |
| size_omitted_default_rule | 22 | | large_document | 4 |
| mid_call_correction | 22 | | unordered_offer_rows | 4 |
| multi_po_document | 18 | | handwritten_correction | 4 |
| missing_po_number | 16 | | ship_to_override_note | 2 |
| zero_qty_rows_trap | 16 | | chat_correction | 2 |
| mixed_currency | 14 | | photo_of_screen | 2 |
| promo_discount_pricing | 8 | | page_upside_down | 1 |
| closed_dc_reroute | 7 | |  |  |

## Gotchas students will hit (on purpose)

- Emails are containers. The order can be in the body, in an attachment, in an inline image, or spread across all three.
- Not every format needs AI, and not every format is suited to the same kind of AI. Work out which is which.
- The Excel totals are **formulas without cached values**. If you read them with pandas you get `NaN`. Don't trust document totals anyway; recompute them.
- A duplicate looks exactly like a valid order. Only retailer + PO number (and content) give it away.
- An amendment is not a new order. It changes lines on an earlier PO.
- On multimodal documents the product is sometimes **only** identifiable from a photo or a caption, and a quantity can be written anywhere on the page.

## About the data

Every document, product photo, stamp, and handwriting sample was generated synthetically. There are no real scans, photos, or customer files in this corpus, and no external images.
