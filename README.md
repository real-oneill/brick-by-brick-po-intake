# Brick-by-Brick @ NYU: Intelligent Purchase Order Intake

The Fall 2026 industry use case for the **Brick-by-Brick** program (Tech@NYU × Databricks).

Maison Solenne, a (fictional) prestige beauty group, receives retailer purchase orders through every channel imaginable: EDI, emailed PDFs, faxes, handwritten forms, Excel buysheets, portal exports, phone calls, chat screenshots, and promo flyers covered in handwriting. Your team will build a governed, AI-powered solution on **Databricks Free Edition** that turns them into correct, fulfillable, auditable sales orders, with a human in the loop.

| Start here | |
|---|---|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | The problem, the requirements, scope tiers, week-by-week plan, target metrics, and the showcase rubric |
| [`data/README.md`](data/README.md) | The synthetic corpus: channels, file formats, complexity levels, every CSV schema, and the issue taxonomy |

## What's in `data/`

```
data/
  master_data/            products, customers, ship-tos, item cross-reference, prices, inventory, retailer rules
  documents/train/        184 inbound documents, one folder per channel (PDF, PNG, JPG, EML, XLSX, CSV, JSON, EDI, TXT)
  ground_truth/train/     the answer key: manifest (incl. complexity 1-4), headers, lines, labeled issues
```

The **holdout set** (48 more documents) is released the week before the Week 11 showcase and scored against a private answer key.

## Ground rules

- **Everything here is synthetic and fictional.** Every company, brand, retailer, person, product, barcode, and price is made up. The scenario is modeled on a real, anonymized engagement.
- **How you build it is up to you.** The requirements say *what* the solution must do, not which features to use. Try options, measure them, and be ready to justify your choices.
- **For educational use** in the Brick-by-Brick program.
