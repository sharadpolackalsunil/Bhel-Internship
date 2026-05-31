# 🚀 Project Journey: Challenges, Solutions, & Testing

Building the MITS Gwalior Result Scraper was a complex task involving web automation, optical character recognition (OCR), and data extraction. Here is a detailed breakdown of the major hurdles we encountered and how we engineered solutions for them.

---

## 🛑 Problem 1: Low CAPTCHA Accuracy
**The Problem:**
Initially, we used a custom-trained Convolutional Neural Network (CNN) to solve the CAPTCHAs. However, the live university portal generates highly distorted and noisy CAPTCHAs, leading to very low accuracy (around 10-20%) and frequent scraper failures.

**The Solution:**
We abandoned the custom CNN and integrated Microsoft's **TrOCR (Transformer-based Optical Character Recognition)** model (`microsoft/trocr-base-printed`) via Hugging Face. Because TrOCR uses an advanced Vision-Encoder-Decoder architecture pre-trained on millions of printed text images, our CAPTCHA accuracy instantly skyrocketed to nearly 100%.

---

## 🛑 Problem 2: The "Ghost" CAPTCHA Failures (Session State)
**The Problem:**
Even after integrating TrOCR and getting 100% correct text predictions, the portal kept rejecting the CAPTCHAs with an "incorrect captcha" alert. 

**The Solution:**
ASP.NET websites rely heavily on hidden session variables (like `__VIEWSTATE`). Our original scraper was navigating directly to the final `Result_BTech.aspx` URL, bypassing the mandatory program selection screen. This resulted in an invalid session on the server side. 
We fixed this by:
1. Navigating to `ProgramSelect.aspx` first.
2. Clicking the "B.Tech." radio button.
3. Selecting the semester from the dropdown.
4. **Crucially**, injecting JavaScript to force the browser to reload the CAPTCHA image with a unique timestamp (`&t=timestamp`) to bypass browser caching and ensure the image matched the server's new session state.

---

## 🛑 Problem 3: Messy Data Extraction
**The Problem:**
After successfully bypassing the CAPTCHA, the final export file (`results.csv`) was a mess. It placed generic text like "Statement of Grade Examination" into the Program column, missed the SGPA entirely, and lumped all subjects into generic `Subj_1` columns. This happened because the scraper was blindly grabbing all HTML tables without understanding the context.

**The Solution:**
We analyzed the exact DOM structure of the result page and completely rewrote the `parse_result_page()` function using BeautifulSoup. 
- We extracted the top header info (Name, Roll No, Branch) using specific ASP.NET `lbl` IDs.
- We accurately targeted the Grades table to extract Course Codes, Credits, and Grades.
- We specifically targeted the Footer table to extract the final Pass/Fail status, SGPA, and CGPA.
- Finally, we updated `export.py` to dynamically generate clean column headers for every individual course code (e.g., `27242201 [T] Grade`).

---

## 🛑 Problem 4: The 1.3GB Git Push Failure
**The Problem:**
When attempting to push the finished project to GitHub, the `git push` command failed completely.

**The Solution:**
The new TrOCR model we downloaded (`model.safetensors`) was 1.33 GB in size, which far exceeded GitHub's strict 100 MB file size limit. 
We performed a `git reset` to undo the broken commits, added the `captcha_model/trocr_model/` directory to our `.gitignore` file, and recreated the commit safely.

---

## 🧪 How We Tested Our Code (The `Test/` Environment)

Instead of running the entire 200+ student pipeline every time we made a change, we built an isolated testing environment. 

1. **Modular Scripts**: We created standalone scripts like `test_submit_sem4.py` and `test_submit_radio.py`. These scripts ran a headless Selenium browser for just a *single* student enrollment number, allowing us to rapidly iterate on the clicking and navigation logic.
2. **Visual Debugging**: Since Selenium was running in "headless" mode (invisible), we used `driver.save_screenshot()` extensively. By saving images like `test_before_fill.png` and `test_radio_captcha.png`, we could literally "see" what the invisible browser was doing and verify if elements were overlapping or hidden.
3. **Offline HTML Parsing**: To fix the messy data extraction, we saved the raw HTML of a successful result page to a local file (`result_page.html`). We then created `test_parse.py` to run our BeautifulSoup logic against this offline file. This allowed us to perfect the table extraction in milliseconds without needing to re-solve a CAPTCHA over the internet every time we tweaked the code.
4. **Cleanup**: Once testing was successful, we integrated the working code back into `scraper.py` and used terminal commands to wipe all temporary test scripts and screenshots to keep the repository clean for production.
