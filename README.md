# 🎓 MITS Gwalior Result Scraper

> **OCR + Deep Learning + Automated Data Extraction Portfolio Project**

Automated pipeline to extract semester results from the MITS Gwalior university portal using a custom-trained CNN for CAPTCHA solving.

---

## 📋 Project Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CAPTCHA Solver | TrOCR (Transformers) | Recognizes 5-char alphanumeric CAPTCHAs with high accuracy |
| Web Scraper | Selenium | Automates form submission on ASP.NET portal |
| Data Processing | Pandas | Sorts, ranks, and exports results |

## 🏗️ Architecture

```
BHEL PROJECT/
├── main.py                     # 🎯 Run the full pipeline
├── requirements.txt
│
├── captcha_model/              # Phase 2: Deep Learning (OCR)
│   ├── predict.py              # TrOCR Inference logic
│   └── trocr_model/            # Downloaded huggingface model weights
│
├── scraper/                    # Phase 3: Automated Pipeline
│   ├── scraper.py              # Selenium-based ASP.NET portal scraper
│   ├── enrollment.py           # Enrollment number generator
│   └── captcha_images/         # Saved CAPTCHAs
│
├── data_processor/             # Phase 4: Data Export
│   └── export.py               # CSV + Excel export with dynamic course formatting
│
└── data/                       # Output
    ├── results.csv             # All 210 students, SGPA ascending
    └── results.xlsx            # 4 sheets: All + per-branch
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. The CAPTCHA Model

This project uses Microsoft's **TrOCR (Transformers-based OCR)**. You do NOT need to train a model from scratch! 

On your first run, the pre-trained Hugging Face model (`microsoft/trocr-base-printed`) will automatically download itself and save to the `captcha_model/trocr_model/` folder.

### 3. Run the Scraper

```bash
# Full pipeline (train + scrape + export)
python main.py

# Scrape only (model must exist)
python main.py --scrape-only

# Scrape specific branch
python main.py --scrape-only --branch BTAD

# Show browser window (debug mode)
python main.py --scrape-only --no-headless
```

### 4. Export Data Only

```bash
python main.py --export-only
```

## 🎓 Enrollment Numbers

| Branch | Code | Range | Count |
|--------|------|-------|-------|
| AI & Data Science | BTAD | BTAD24O1001 → BTAD24O1070 | 70 |
| AI & Machine Learning | BTAM | BTAM24O1001 → BTAM24O1070 | 70 |
| Artificial Intelligence | BTAI | BTAI24O1001 → BTAI24O1070 | 70 |
| **Total** | | | **210** |

## 🧠 CAPTCHA Solving Engine

### Architecture
This project utilizes **Microsoft's TrOCR** (Transformer-based Optical Character Recognition) to decode CAPTCHAs accurately without any complex preprocessing pipelines.

```
Input: Raw CAPTCHA image
  │
  ▼
TrOCRProcessor (microsoft/trocr-base-printed)
  │
  ▼
VisionEncoderDecoderModel
  │
  ▼
Output String (with whitespace stripped)
```

### Solving Strategy

```
CAPTCHA Image (Fetched via JS Canvas Base64)
     │
     ▼
  TrOCR Prediction 
     │
     ▼
  Strip Whitespace ─────────────────────► Final Text
```

## 📊 Output Format

### CSV (`results.csv`)
All 210 students sorted by SGPA (ascending), includes: enrollment, name, branch, SGPA, CGPA, pass/fail status, and dynamically generated columns for every course (Total Credit, Earned Credit, and Grade).

### Excel (`results.xlsx`)
4 sheets with formatted tables:
| Sheet | Content |
|-------|---------|
| All Students | Combined view, sorted by SGPA |
| AI_DS | BTAD students with branch rank |
| AI_ML | BTAM students with branch rank |
| AI | BTAI students with branch rank |

Features: Color-coded SGPA (🟢 ≥9.0, 🟡 ≥7.5, 🔴 <5.0), pass/fail highlighting, auto-filters, frozen headers.

## 📝 CLI Reference

```
python main.py [OPTIONS]

Modes:
  --scrape-only    Run the scraper (default if no mode specified)
  --export-only    Only export data from raw JSON to CSV/Excel

Scraping:
  --model PATH     Path to trained model
  --no-headless    Show browser window
  --branch CODE    Filter branches (BTAD, BTAM, BTAI)
  --no-resume      Start fresh (ignore checkpoint)

Export:
  --raw-input PATH  Path to raw results JSON
```

## 🛡️ Features

- **Checkpoint Recovery**: Saves progress every 10 students. Resume with `--resume` (default)
- **Rate Limiting**: 2-4 second random delays between requests
- **Retry Logic**: Up to 5 CAPTCHA retries per student
- **Error Handling**: Graceful handling of timeouts, missing records, and CAPTCHA failures
- **Dual Export**: CSV for data analysis, Excel for presentation

## ⚙️ Tech Stack

- **Python 3.10+**
- **Transformers (Hugging Face)** — TrOCR model for OCR
- **PyTorch** — Deep learning backend for TrOCR
- **Selenium** — Browser automation for ASP.NET portal
- **Pandas** — Data processing and export
- **Pillow** — Image handling
- **BeautifulSoup4** — HTML result parsing

---

*Built as a portfolio project demonstrating OCR, Deep Learning, and automated data extraction.*
