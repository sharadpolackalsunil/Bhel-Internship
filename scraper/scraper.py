"""
MITS Gwalior Result Portal Scraper
=====================================
Scrapes semester results from the live MITS Gwalior university portal:
    https://iums.mitsgwalior.in/Result/Result_BTech.aspx

Strategy:
    1. Selenium for browser automation (handles ASP.NET ViewState + JavaScript)
    2. CNN-based CAPTCHA solving (primary) with OCR fallback
    3. Rate-limited requests (2-4 second delays)
    4. Checkpoint-based progress saving
    5. Retry logic for failed CAPTCHAs

Dependencies:
    - selenium + webdriver-manager (auto-downloads ChromeDriver)
    - captcha_model (CNN solver)
    - beautifulsoup4 (HTML parsing)
"""

import os
import sys
import time
import json
import random
import csv
from datetime import datetime
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

from PIL import Image
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.enrollment import (
    generate_enrollment_numbers, BRANCHES, SEMESTER
)
from captcha_model.predict import CaptchaSolver


# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

RESULT_URL = "https://iums.mitsgwalior.in/Result/Result_BTech.aspx"
PROGRAM_SELECT_URL = "https://iums.mitsgwalior.in/Result/ProgramSelect.aspx"

# Timing
MIN_DELAY = 2.0    # Minimum delay between requests (seconds)
MAX_DELAY = 4.0    # Maximum delay between requests
PAGE_LOAD_TIMEOUT = 15  # Selenium page load timeout

# Retry
MAX_CAPTCHA_RETRIES = 5   # Max retries per student if CAPTCHA fails
MAX_TOTAL_RETRIES = 3     # Max retries per student for other errors

# Checkpoint
CHECKPOINT_INTERVAL = 10  # Save progress every N students


# ──────────────────────────────────────────────────────────────
# Selenium WebDriver Setup
# ──────────────────────────────────────────────────────────────

def create_driver(headless=True):
    """
    Create and configure a Chrome WebDriver instance.

    Args:
        headless: Run browser without GUI.

    Returns:
        selenium.webdriver.Chrome instance
    """
    chrome_options = Options()

    if headless:
        chrome_options.add_argument('--headless=new')

    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280,720')

    # Mimic real browser
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # Disable automation flags
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        if ChromeDriverManager:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
    except WebDriverException:
        # Fallback: try without webdriver-manager
        driver = webdriver.Chrome(options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


# ──────────────────────────────────────────────────────────────
# CAPTCHA Handling
# ──────────────────────────────────────────────────────────────

def download_captcha_image(driver, save_dir=None):
    """
    Download the CAPTCHA image from the result page.

    Uses Selenium to screenshot the CAPTCHA element, which avoids
    issues with session-bound image URLs.

    Args:
        driver: Selenium WebDriver instance.
        save_dir: Optional directory to save CAPTCHA images.

    Returns:
        PIL.Image: The CAPTCHA image.
    """
    try:
        # Find CAPTCHA image element
        # Common ASP.NET CAPTCHA element IDs
        captcha_selectors = [
            "imgCaptcha",
            "CaptchaImage",
            "captchaImage",
            "Image1",
            "imgVarification",
        ]

        captcha_element = None
        for selector in captcha_selectors:
            try:
                captcha_element = driver.find_element(By.ID, selector)
                break
            except NoSuchElementException:
                continue

        if captcha_element is None:
            # Try finding by XPath — look for img near the CAPTCHA text
            try:
                captcha_element = driver.find_element(
                    By.XPATH,
                    "//img[contains(@src, 'Captcha') or contains(@src, 'captcha') "
                    "or contains(@id, 'Captcha') or contains(@id, 'captcha') "
                    "or contains(@id, 'img')]"
                )
            except NoSuchElementException:
                # Try finding any image that looks like a CAPTCHA
                images = driver.find_elements(By.TAG_NAME, 'img')
                for img in images:
                    src = img.get_attribute('src') or ''
                    if 'captcha' in src.lower() or 'handler' in src.lower():
                        captcha_element = img
                        break

        if captcha_element is None:
            raise RuntimeError("Could not find CAPTCHA image element on page")

        # Method 1: Screenshot the element directly
        png_bytes = captcha_element.screenshot_as_png
        captcha_img = Image.open(BytesIO(png_bytes))

        # Save for training data collection (optional)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            save_path = os.path.join(save_dir, f"captcha_{timestamp}.png")
            captcha_img.save(save_path)

        return captcha_img

    except Exception as e:
        print(f"  ❌ Error downloading CAPTCHA: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# Result Parsing
# ──────────────────────────────────────────────────────────────

def parse_result_page(driver):
    """
    Parse the result page after successful form submission.
    Extracts all available student data.

    Args:
        driver: Selenium WebDriver (on the result page).

    Returns:
        dict: Extracted student data, or None if result not found.
    """
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        result_data = {}

        # Check for error messages (invalid enrollment, wrong CAPTCHA, etc.)
        error_indicators = [
            'invalid', 'not found', 'error', 'incorrect',
            'wrong captcha', 'try again', 'no record'
        ]
        page_text = soup.get_text().lower()
        for indicator in error_indicators:
            if indicator in page_text and 'result' not in page_text[:100].lower():
                return None

        # Strategy: Extract data from table rows or labeled fields
        # ASP.NET result pages typically use tables or div-based layouts

        # Method 1: Look for labeled fields (Label: Value pairs)
        all_text = soup.get_text(separator='\n')
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]

        # Try to find specific fields
        field_mapping = {
            'enrollment': ['enrollment', 'enrol', 'roll no', 'roll number'],
            'student_name': ['name', 'student name', 'candidate'],
            'father_name': ['father', 'father name', "father's"],
            'program': ['program', 'programme', 'course', 'branch'],
            'semester': ['semester', 'sem'],
            'sgpa': ['sgpa', 's.g.p.a', 'semester gpa'],
            'cgpa': ['cgpa', 'c.g.p.a', 'cumulative gpa'],
            'result_status': ['result', 'status', 'pass', 'fail'],
            'total_marks': ['total', 'total marks', 'aggregate'],
            'max_marks': ['max marks', 'maximum'],
        }

        for key, search_terms in field_mapping.items():
            for i, line in enumerate(lines):
                line_lower = line.lower()
                for term in search_terms:
                    if term in line_lower:
                        # Try to extract value from same line or next line
                        # Pattern: "Label: Value" or "Label\nValue"
                        if ':' in line:
                            value = line.split(':', 1)[1].strip()
                            if value:
                                result_data[key] = value
                                break
                        elif i + 1 < len(lines):
                            result_data[key] = lines[i + 1]
                            break
                if key in result_data:
                    break

        # Method 2: Parse tables for subject-wise marks
        tables = soup.find_all('table')
        subjects = []

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:
                # Check if this looks like a marks table
                header_row = rows[0]
                headers = [th.get_text(strip=True) for th in
                           header_row.find_all(['th', 'td'])]

                # Look for subject/marks headers
                header_lower = ' '.join(headers).lower()
                if any(h in header_lower for h in
                       ['subject', 'marks', 'grade', 'credit']):
                    for row in rows[1:]:
                        cells = [td.get_text(strip=True) for td in
                                 row.find_all('td')]
                        if cells and len(cells) >= 2:
                            subject = {
                                f'col_{j}': cell
                                for j, cell in enumerate(cells)
                            }
                            subjects.append(subject)

        if subjects:
            result_data['subjects'] = subjects

        # Method 3: Try to find SGPA/CGPA from any span/div with numeric value
        if 'sgpa' not in result_data:
            for tag in soup.find_all(['span', 'td', 'div', 'label']):
                tag_id = (tag.get('id') or '').lower()
                tag_text = tag.get_text(strip=True)
                if 'sgpa' in tag_id or 'gpa' in tag_id:
                    try:
                        val = float(tag_text)
                        if 0 <= val <= 10:
                            result_data['sgpa'] = str(val)
                    except (ValueError, TypeError):
                        pass

        # Method 4: Look for result status (Pass/Fail)
        if 'result_status' not in result_data:
            for tag in soup.find_all(['span', 'td', 'div', 'label']):
                text = tag.get_text(strip=True).upper()
                if text in ['PASS', 'FAIL', 'PROMOTED', 'DETAINED',
                            'COMPARTMENT', 'RE-APPEAR']:
                    result_data['result_status'] = text
                    break

        return result_data if result_data else None

    except Exception as e:
        print(f"  ❌ Error parsing result: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# Main Scraper
# ──────────────────────────────────────────────────────────────

def scrape_student_result(driver, enrollment_no, semester, captcha_solver,
                          captcha_save_dir=None):
    """
    Scrape result for a single student.

    Args:
        driver: Selenium WebDriver.
        enrollment_no: e.g., 'BTAD24O1001'
        semester: Semester number (4).
        captcha_solver: CaptchaSolver instance.
        captcha_save_dir: Optional dir to save CAPTCHA images.

    Returns:
        dict: Student result data, or None if failed.
    """
    for attempt in range(MAX_CAPTCHA_RETRIES):
        try:
            # Navigate to result page
            driver.get(RESULT_URL)
            time.sleep(1)

            # Wait for page to load
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )

            # Fill enrollment number
            enrollment_input = None
            input_selectors = [
                "txtEnrollmentNo", "txt_enrollment", "txtEnrol",
                "TextBox1", "txtRollNo"
            ]

            for sel in input_selectors:
                try:
                    enrollment_input = driver.find_element(By.ID, sel)
                    break
                except NoSuchElementException:
                    continue

            if enrollment_input is None:
                # Fallback: find by type
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    inp_type = inp.get_attribute('type') or ''
                    inp_id = (inp.get_attribute('id') or '').lower()
                    if inp_type.lower() == 'text' and 'enrol' in inp_id:
                        enrollment_input = inp
                        break
                    if inp_type.lower() == 'text' and 'roll' in inp_id:
                        enrollment_input = inp
                        break

            if enrollment_input is None:
                # Last resort: first visible text input
                inputs = driver.find_elements(
                    By.CSS_SELECTOR, "input[type='text']"
                )
                if inputs:
                    enrollment_input = inputs[0]

            if enrollment_input is None:
                raise RuntimeError("Cannot find enrollment input field")

            enrollment_input.clear()
            enrollment_input.send_keys(enrollment_no)

            # Select semester
            try:
                semester_selectors = [
                    "ddlSemester", "ddl_semester", "DropDownList1",
                    "ddlSem", "ddlChooseSemester"
                ]
                semester_dropdown = None
                for sel in semester_selectors:
                    try:
                        semester_dropdown = driver.find_element(By.ID, sel)
                        break
                    except NoSuchElementException:
                        continue

                if semester_dropdown is None:
                    selects = driver.find_elements(By.TAG_NAME, 'select')
                    if selects:
                        semester_dropdown = selects[0]

                if semester_dropdown:
                    select = Select(semester_dropdown)
                    select.select_by_value(str(semester))
            except Exception:
                try:
                    select = Select(semester_dropdown)
                    select.select_by_visible_text(str(semester))
                except Exception:
                    pass

            time.sleep(0.5)

            # Download and solve CAPTCHA
            captcha_img = download_captcha_image(driver, captcha_save_dir)
            if captcha_img is None:
                print(f"  ⚠️  Could not download CAPTCHA (attempt {attempt+1})")
                continue

            captcha_text, confidence = captcha_solver.solve(captcha_img)
            print(f"  CAPTCHA: '{captcha_text}' (conf: {confidence:.3f})")

            # Enter CAPTCHA text
            captcha_input_selectors = [
                "txtCaptcha", "txtVerification", "txtVarification",
                "TextBox2", "txtCode", "txtCaptchaCode"
            ]
            captcha_input = None
            for sel in captcha_input_selectors:
                try:
                    captcha_input = driver.find_element(By.ID, sel)
                    break
                except NoSuchElementException:
                    continue

            if captcha_input is None:
                # Find text input near the CAPTCHA image
                inputs = driver.find_elements(
                    By.CSS_SELECTOR, "input[type='text']"
                )
                # Usually the CAPTCHA input is the second or last text input
                if len(inputs) >= 2:
                    captcha_input = inputs[-1]  # Last text input

            if captcha_input is None:
                raise RuntimeError("Cannot find CAPTCHA input field")

            captcha_input.clear()
            captcha_input.send_keys(captcha_text)

            # Click submit button
            submit_selectors = [
                "btnViewResult", "btnSubmit", "Button1",
                "btnResult", "btnShow"
            ]
            submit_btn = None
            for sel in submit_selectors:
                try:
                    submit_btn = driver.find_element(By.ID, sel)
                    break
                except NoSuchElementException:
                    continue

            if submit_btn is None:
                # Find by button text
                buttons = driver.find_elements(By.TAG_NAME, 'input')
                for btn in buttons:
                    btn_type = (btn.get_attribute('type') or '').lower()
                    btn_value = (btn.get_attribute('value') or '').lower()
                    if btn_type == 'submit' or 'result' in btn_value or 'view' in btn_value:
                        submit_btn = btn
                        break

            if submit_btn is None:
                raise RuntimeError("Cannot find submit button")

            submit_btn.click()

            # Wait for result page to load
            time.sleep(2)

            # Check for CAPTCHA error (wrong CAPTCHA → page reloads)
            page_text = driver.page_source.lower()
            if 'incorrect' in page_text or 'wrong' in page_text:
                print(f"  ⚠️  Wrong CAPTCHA (attempt {attempt+1}/{MAX_CAPTCHA_RETRIES})")
                continue

            # Parse results
            result = parse_result_page(driver)
            if result is not None:
                result['enrollment'] = enrollment_no
                result['semester'] = str(semester)
                return result
            else:
                print(f"  ⚠️  No result found for {enrollment_no}")
                return {'enrollment': enrollment_no, 'semester': str(semester),
                        'result_status': 'NOT_FOUND'}

        except TimeoutException:
            print(f"  ⚠️  Timeout (attempt {attempt+1})")
            continue
        except Exception as e:
            print(f"  ❌ Error: {e} (attempt {attempt+1})")
            continue

    print(f"  ❌ Failed all {MAX_CAPTCHA_RETRIES} attempts for {enrollment_no}")
    return {'enrollment': enrollment_no, 'semester': str(semester),
            'result_status': 'SCRAPE_FAILED'}


# ──────────────────────────────────────────────────────────────
# Checkpoint Management
# ──────────────────────────────────────────────────────────────

def save_checkpoint(results, checkpoint_path):
    """Save current results to a checkpoint file."""
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_checkpoint(checkpoint_path):
    """Load results from a checkpoint file."""
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


# ──────────────────────────────────────────────────────────────
# Main Scrape Pipeline
# ──────────────────────────────────────────────────────────────

def run_scraper(model_path=None, headless=True, save_captchas=True,
                branch_filter=None, resume=True):
    """
    Run the full scraping pipeline for all students.

    Args:
        model_path: Path to trained CAPTCHA CNN model.
        headless: Run browser without GUI.
        save_captchas: Save downloaded CAPTCHA images (for training data).
        branch_filter: Optional list of branch codes to scrape (e.g., ['BTAD']).
        resume: Resume from checkpoint if available.

    Returns:
        List of result dictionaries.
    """
    # Setup paths
    data_dir = os.path.join(project_root, 'data')
    raw_dir = os.path.join(data_dir, 'raw')
    captcha_dir = os.path.join(project_root, 'scraper', 'captcha_images')
    checkpoint_path = os.path.join(data_dir, 'scrape_checkpoint.json')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    print("=" * 60)
    print("MITS Gwalior Result Scraper")
    print("=" * 60)
    print(f"  Target:    {RESULT_URL}")
    print(f"  Semester:  {SEMESTER}")
    print(f"  Headless:  {headless}")
    print(f"  Delay:     {MIN_DELAY}-{MAX_DELAY}s")
    print("=" * 60)

    # Load CAPTCHA solver
    print("\n📦 Loading CAPTCHA solver...")
    solver = CaptchaSolver(model_path=model_path)

    # Generate enrollment numbers
    enrollments = generate_enrollment_numbers()
    if branch_filter:
        enrollments = [
            (e, name, short)
            for e, name, short in enrollments
            if any(e.startswith(BRANCHES[b]['prefix']) for b in branch_filter)
        ]

    total = len(enrollments)
    print(f"\n🎓 Students to scrape: {total}")

    # Resume from checkpoint
    results = []
    scraped_enrollments = set()
    if resume:
        results = load_checkpoint(checkpoint_path)
        scraped_enrollments = {r.get('enrollment') for r in results}
        if scraped_enrollments:
            print(f"📋 Resuming from checkpoint: {len(scraped_enrollments)} already scraped")

    # Create WebDriver
    print("\n🌐 Starting browser...")
    driver = create_driver(headless=headless)

    try:
        # First, navigate to program selection to "warm up" the session
        driver.get(PROGRAM_SELECT_URL)
        time.sleep(2)

        # Progress bar
        pending = [
            (e, name, short)
            for e, name, short in enrollments
            if e not in scraped_enrollments
        ]

        pbar = tqdm(pending, desc="Scraping results", unit="student")

        for idx, (enrollment, branch_name, branch_short) in enumerate(pbar):
            pbar.set_postfix({
                'enrollment': enrollment,
                'branch': branch_short,
                'done': len(results)
            })

            # Scrape this student
            result = scrape_student_result(
                driver, enrollment, SEMESTER, solver,
                captcha_save_dir=captcha_dir if save_captchas else None
            )

            if result:
                result['branch'] = branch_name
                result['branch_short'] = branch_short
                results.append(result)

            # Save checkpoint periodically
            if (idx + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(results, checkpoint_path)

            # Rate limiting
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

        # Final save
        save_checkpoint(results, checkpoint_path)

    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user. Saving progress...")
        save_checkpoint(results, checkpoint_path)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        save_checkpoint(results, checkpoint_path)
        raise
    finally:
        driver.quit()
        print("🌐 Browser closed.")

    # Save raw results
    raw_path = os.path.join(raw_dir, f'raw_results_{SEMESTER}.json')
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Raw results saved to: {raw_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Scraping Summary")
    print("=" * 60)
    print(f"  Total scraped:  {len(results)}")
    for code, info in BRANCHES.items():
        branch_count = sum(
            1 for r in results if r.get('branch_short') == info['short_name']
        )
        print(f"  {info['name']}: {branch_count}")

    success_count = sum(
        1 for r in results
        if r.get('result_status', '').upper() not in ['NOT_FOUND', 'SCRAPE_FAILED']
    )
    print(f"  Successful:     {success_count}")
    print(f"  Failed:         {len(results) - success_count}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MITS Result Scraper")
    parser.add_argument('--model', type=str, default=None,
                        help='Path to trained CAPTCHA model')
    parser.add_argument('--no-headless', action='store_true',
                        help='Show browser window')
    parser.add_argument('--branch', type=str, nargs='+',
                        choices=['BTAD', 'BTAM', 'BTAI'],
                        help='Scrape specific branches only')
    parser.add_argument('--no-resume', action='store_true',
                        help='Start fresh (ignore checkpoint)')
    args = parser.parse_args()

    results = run_scraper(
        model_path=args.model,
        headless=not args.no_headless,
        branch_filter=args.branch,
        resume=not args.no_resume,
    )
