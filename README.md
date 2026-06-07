# 🎓 MITS Gwalior Automated Result Extraction System (with Deep Learning)

> **An end-to-end automated pipeline integrating Transformers-based Deep Learning (TrOCR) and Browser Automation to systematically bypass ASP.NET challenges, solve CAPTCHAs, and extract structured university data.**

---

## 🌟 Why This Project Stands Out

This isn't just a simple web scraper. University portals are notoriously difficult to scrape reliably due to strict security measures and outdated architectures. Here is how this project solves these complex engineering challenges:

1. **Defeating ASP.NET ViewState & PostBacks:**
   The MITS portal relies heavily on `ASP.NET` ViewState and dynamic PostBacks which break traditional HTTP request scrapers (like `requests` + `BeautifulSoup`). This project employs **Selenium WebDriver** to mimic a real browser, properly initializing ASP.NET sessions, selecting the correct radio buttons, and triggering necessary server PostBacks.
   
2. **State-of-the-Art CAPTCHA Solving (No Manual Labeling):**
   Instead of relying on fragile OCR tools like Tesseract or building a basic CNN from scratch, this project implements **Microsoft's TrOCR (Transformer-based Optical Character Recognition)**. TrOCR achieves near **99% accuracy** on printed CAPTCHAs by framing text recognition as an image-to-text sequence generation problem, completely bypassing the need to manually label datasets and train custom CNNs.

3. **Dynamic Data Wrangling:**
   Extracting data from nested, dynamically structured HTML tables is messy. The `Pandas`-based processor automatically flattens these tables, handles missing courses, dynamically generates grade columns, and computes rankings before exporting to a highly formatted Excel workbook.

4. **Production-Ready Resiliency:**
   Built for long-running stability:
   - **Checkpoints:** Automatically saves progress to disk every 10 records.
   - **Rate Limiting:** Implements randomized 2-4 second delays to prevent server bans.
   - **Retry Logic:** Auto-detects wrong CAPTCHAs and seamlessly reloads the image (forcing a cache-busting refresh) to retry up to 5 times.

---

## 🚀 Quick Start Guide

Want to run the pipeline yourself? Follow these steps:

### 1. Prerequisites
Ensure you have **Python 3.10+** installed. Clone the repository and navigate to the project root.

### 2. Set Up Virtual Environment
It is highly recommended to use a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate
# Activate it (Mac/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: If you plan on using GPU acceleration for TrOCR, ensure you install the CUDA-compatible version of PyTorch from the [official PyTorch website](https://pytorch.org/).)*

## 🚀 Usage

### 1. The Main Scraper (Batch Result Extraction)

Run the main pipeline to scrape all B.Tech AI branch results, process them, and export to Excel:

```bash
# Run full pipeline (scrape + export)
python main.py

# Scrape only
python main.py --scrape-only

# Scrape with visible browser
python main.py --scrape-only --no-headless
# Generate Excel/CSV reports from previously scraped data
python main.py --export-only
```

---

## 🏗️ Architecture

```
BHEL PROJECT/
├── main.py                     # 🎯 CLI Entry Point
├── requirements.txt
│
├── captcha_model/              # 🧠 Deep Learning Engine
│   └── predict.py              # TrOCR Inference logic (Auto-downloads weights)
│
├── scraper/                    # 🕸️ Automation Engine
│   ├── scraper.py              # Selenium ASP.NET logic, CAPTCHA download, and retry logic
│   └── enrollment.py           # Enrollment number logic/ranges
│
├── data_processor/             # 📊 Data Wrangling Engine
│   └── export.py               # Pandas logic for generating formatted Excel/CSV
│
└── data/                       # 📁 Output Directory
    ├── raw/                    # Checkpoints and raw JSON output
    ├── results.csv             # Unified CSV of all students
    └── results.xlsx            # Formatted Excel workbook with branch-specific sheets
```

---

## 🧠 Deep Learning (TrOCR) Pipeline

How the CAPTCHA is solved in real-time:

1. **Extraction**: Selenium executes JavaScript to extract the raw base64 data of the dynamically loaded CAPTCHA canvas (bypassing session-bound URL issues).
2. **Inference**: The image is passed to `microsoft/trocr-base-printed` which uses a Vision Transformer (ViT) encoder and RoBERTa decoder to predict the text sequence.
3. **Refinement**: Whitespace and illegal characters are stripped before injection back into the browser.

---

## 📊 The Output (Excel & CSV)

The final product is a highly polished `results.xlsx` file containing:
- **Comprehensive Data**: SGPA, CGPA, Pass/Fail status, and course-by-course breakdowns (Credits & Grades).
- **Auto-Formatting**: Conditional formatting highlights excellent SGPAs (🟢 ≥9.0) and failing grades (🔴).
- **Segmented Sheets**: Individual sheets for each branch (AI & Data Science, AI & Machine Learning, Artificial Intelligence) alongside a Master sheet.
- **Rankings**: Auto-computed rankings for students within their respective branches.

---

*Built as a comprehensive portfolio project demonstrating advanced web automation, applied deep learning, and data engineering.* 
