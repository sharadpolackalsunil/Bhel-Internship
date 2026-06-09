# 🎓 MITS Gwalior Automated Extraction & Analytics Dashboard

> **An end-to-end full-stack pipeline integrating Transformers-based Deep Learning (TrOCR), Browser Automation, a FastAPI backend, and a modern React dashboard to systematically extract, process, and visualize structured university data.**

---

## 🌟 Why This Project Stands Out

This isn't just a simple web scraper. University portals are notoriously difficult to scrape reliably due to strict security measures and outdated architectures. Here is how this project solves these complex engineering challenges:

1. **Defeating ASP.NET ViewState & PostBacks:**
   The MITS portal relies heavily on `ASP.NET` ViewState and dynamic PostBacks which break traditional HTTP request scrapers. This project employs **Selenium WebDriver** to mimic a real browser, properly initializing ASP.NET sessions, selecting correct radio buttons, and triggering necessary server PostBacks.
   
2. **State-of-the-Art CAPTCHA Solving (No Manual Labeling):**
   Instead of relying on fragile OCR tools like Tesseract, this project implements **Microsoft's TrOCR (Transformer-based Optical Character Recognition)**. TrOCR achieves near **99% accuracy** on printed CAPTCHAs by framing text recognition as an image-to-text sequence generation problem.

3. **Comprehensive Data Extraction:**
   The scraper navigates through complex multi-page workflows to extract:
   - **Personal Profiles**: Demographics, contact info, and addresses.
   - **Academic History**: Semester-by-semester SGPA and final CGPA.
   - **Fee Status**: Payment dates, amounts, and statuses.
   - **Result Sheets**: Course-by-course breakdowns and pass/fail statuses.

4. **Modern Analytics Dashboard:**
   A stunning, interactive frontend built with **React and Recharts**, powered by a high-performance **FastAPI** backend. It features statistical visualizer cards, dynamic charts, student rankings, and incredibly detailed individual student profiles tracking academic growth trajectories.

---

## 🚀 Quick Start Guide

Want to run the full stack yourself? Follow these steps:

### 1. Prerequisites
Ensure you have **Python 3.10+** and **Node.js 18+** installed. Clone the repository and navigate to the project root.

### 2. Set Up Virtual Environment & Python Dependencies
It is highly recommended to use a virtual environment:
```bash
# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install Python dependencies (Scraper + FastAPI)
pip install -r requirements.txt
```

### 3. Set Up the Frontend
```bash
cd frontend
npm install
```

### 4. Running the Dashboard

You need two terminals to run the full stack:

**Terminal 1 (FastAPI Backend):**
```bash
# From the project root directory
.\venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

**Terminal 2 (React Frontend):**
```bash
# From the frontend/ directory
npm run dev
```

The frontend will load up on `http://localhost:5173/`.

### 5. Running the Scraper
The TrOCR model will **automatically download** from Hugging Face on the first run.
```bash
# Scrape all data
python main.py
```

---

## 🏗️ Full-Stack Architecture

```
BHEL PROJECT/
├── api/                        # ⚡ FastAPI Backend
│   └── main.py                 # Serves CSV data as JSON endpoints
│
├── frontend/                   # 🎨 React + Vite Dashboard
│   ├── src/pages/              # Dashboard, Students List, Student Detail pages
│   └── src/components/         # Reusable UI components
│
├── captcha_model/              # 🧠 Deep Learning Engine
│   └── predict.py              # TrOCR Inference logic
│
├── scraper/                    # 🕸️ Automation Engine
│   ├── iums_scraper.py         # Advanced multi-page extraction (Fees, Profile, Academic)
│   ├── scraper.py              # Base Selenium logic and CAPTCHA solving
│   └── enrollment.py           # Enrollment number generation
│
└── data/                       # 📁 Output Directory (Git Ignored for Security)
    ├── iums_profile.csv        # Extracted student personal details
    ├── iums_academic.csv       # Extracted academic history and grades
    └── iums_fee.csv            # Extracted fee payment records
```

---

## 📊 The Analytics Dashboard

The React dashboard visualizes the extracted data into actionable insights:
- **Results & Analytics**: Stat cards, SGPA distribution charts, branch averages, pass/fail donuts, and Top 10 department rankings.
- **Student Profiles Grid**: Searchable, visual grid of all extracted students with their current standing.
- **Detailed Drill-downs**: Clicking a student reveals their personal details, fee timelines, academic history, and a dynamically normalized line chart showcasing their SGPA vs. Running CGPA growth trajectory.

---

*Built as a comprehensive project demonstrating advanced web automation, applied deep learning, data engineering, and modern full-stack web development.* 
