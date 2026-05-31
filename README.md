# 🎓 MITS Gwalior Result Scraper

> **OCR + Deep Learning + Automated Data Extraction Portfolio Project**

Automated pipeline to extract semester results from the MITS Gwalior university portal using a custom-trained CNN for CAPTCHA solving.

---

## 📋 Project Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CAPTCHA Solver | PyTorch CNN | Recognizes 5-char alphanumeric CAPTCHAs |
| Image Processing | OpenCV | Preprocessing pipeline (grayscale → threshold → clean) |
| Web Scraper | Selenium | Automates form submission on ASP.NET portal |
| Data Processing | Pandas | Sorts, ranks, and exports results |
| OCR Fallback | pytesseract | Backup solver when CNN confidence is low |

## 🏗️ Architecture

```
BHEL PROJECT/
├── main.py                     # 🎯 Run the full pipeline
├── requirements.txt
├── train_colab.ipynb           # 🧠 Google Colab training notebook
│
├── captcha_model/              # Phase 2: Deep Learning
│   ├── dataset.py              # Synthetic CAPTCHA generator
│   ├── model.py                # CNN architecture (multi-head)
│   ├── train.py                # Training script
│   ├── predict.py              # Inference + fallback logic
│   ├── preprocess.py           # OpenCV preprocessing
│   └── saved_models/
│       └── captcha_cnn.pth     # Trained model weights
│
├── scraper/                    # Phase 3: Automated Pipeline
│   ├── scraper.py              # Selenium-based portal scraper
│   ├── enrollment.py           # Enrollment number generator
│   └── captcha_images/         # Downloaded CAPTCHAs (for training)
│
├── data_processor/             # Phase 4: Data Export
│   └── export.py               # CSV + Excel export with formatting
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

### 2. Train the CAPTCHA Model

**Option A: Google Colab (Recommended — Free GPU)**
1. Upload `train_colab.ipynb` to Google Colab
2. Enable GPU: `Runtime → Change runtime type → T4 GPU`
3. Run all cells
4. Download `captcha_cnn.pth` and place it in `captcha_model/saved_models/`

**Option B: Local Training**
```bash
python main.py --train-only --epochs 30 --batch-size 64
```

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

## 🧠 CNN Model

### Architecture

```
Input: Grayscale (1 × 80 × 200)
  │
  ├── Conv Block 1: 1→32 channels (Conv→BN→ReLU→MaxPool)
  ├── Conv Block 2: 32→64
  ├── Conv Block 3: 64→128
  └── Conv Block 4: 128→256
  │
  ├── Flatten: 256×5×12 = 15,360
  ├── FC: 15,360 → 1,024 → 512
  │
  └── 5 Classification Heads (one per character position)
      ├── Head 1: 512 → 36 classes (A-Z, 0-9)
      ├── Head 2: 512 → 36
      ├── Head 3: 512 → 36
      ├── Head 4: 512 → 36
      └── Head 5: 512 → 36
```

### Training Details

- **Dataset**: 50,000 synthetic CAPTCHAs (on-the-fly generation)
- **Loss**: Sum of CrossEntropy for each character position
- **Optimizer**: Adam (lr=1e-3, weight_decay=1e-5)
- **Scheduler**: ReduceLROnPlateau (patience=5)
- **Early Stopping**: patience=7 epochs

### Hybrid Solving Strategy

```
CAPTCHA Image
     │
     ▼
  OpenCV Preprocessing
  (grayscale → blur → threshold → morphology → resize)
     │
     ▼
  CNN Prediction ──── confidence ≥ 0.7? ──── YES → Use CNN result
     │                                              │
     NO                                             │
     │                                              │
     ▼                                              │
  pytesseract OCR (fallback) ─────────────────────► Final Text
```

## 📊 Output Format

### CSV (`results.csv`)
All 210 students sorted by SGPA (ascending), includes: enrollment, name, branch, SGPA, CGPA, pass/fail status, grades.

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
  --train-only     Only train the CNN model
  --scrape-only    Only run the scraper
  --export-only    Only export data

Training:
  --epochs N       Training epochs (default: 30)
  --batch-size N   Batch size (default: 64)
  --lr RATE        Learning rate (default: 0.001)
  --train-size N   Training samples (default: 50000)

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
- **PyTorch** — CNN model training and inference
- **OpenCV** — Image preprocessing pipeline
- **Selenium** — Browser automation for ASP.NET portal
- **Pandas** — Data processing and export
- **Pillow** — CAPTCHA image generation
- **BeautifulSoup4** — HTML result parsing
- **pytesseract** — OCR fallback

---

*Built as a portfolio project demonstrating OCR, Deep Learning, and automated data extraction.*
