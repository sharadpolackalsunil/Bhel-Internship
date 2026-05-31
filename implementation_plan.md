# MITS Gwalior Result Scraper — Final Implementation Plan

## Decisions Made
- ✅ **Real scraper only** — no mock Flask server
- ✅ **Synthetic CAPTCHA data** — no manual labeling
- ✅ **Extract ALL details** — name, enrollment, grades, pass/fail, SGPA
- ✅ **Google Colab** for model training
- ✅ **Hybrid approach** — CNN primary, pytesseract fallback
- ✅ Sort by SGPA **ascending** order
- ✅ Export to CSV + Excel (per-branch sheets)

## Architecture

```
BHEL PROJECT/
├── README.md
├── requirements.txt
│
├── captcha_model/
│   ├── dataset.py              # Synthetic CAPTCHA generator + Dataset
│   ├── model.py                # PyTorch CNN (5-head classifier)
│   ├── train.py                # Training script (Colab-compatible)
│   ├── predict.py              # Inference + fallback logic
│   ├── preprocess.py           # OpenCV preprocessing
│   └── saved_models/
│       └── captcha_cnn.pth
│
├── scraper/
│   ├── scraper.py              # Real portal scraper
│   ├── enrollment.py           # Enrollment number generator
│   └── captcha_images/         # Downloaded CAPTCHAs
│
├── data_processor/
│   └── export.py               # Pandas processing + CSV/Excel export
│
├── data/
│   ├── results.csv
│   └── results.xlsx
│
├── train_colab.ipynb           # Google Colab training notebook
└── main.py                     # Orchestrator — run full pipeline
```

## Execution: Build in this order
1. requirements.txt + project structure
2. captcha_model/dataset.py (synthetic generator)
3. captcha_model/model.py (CNN)
4. captcha_model/train.py + train_colab.ipynb
5. captcha_model/preprocess.py + predict.py
6. scraper/enrollment.py
7. scraper/scraper.py (real portal)
8. data_processor/export.py
9. main.py
10. README.md
