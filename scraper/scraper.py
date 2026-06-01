"""
MITS Gwalior Result Portal Scraper
=====================================
Scrapes semester results from the live MITS Gwalior university portal:
    https://iums.mitsgwalior.in/Result/Result_BTech.aspx

Strategy:
    1. Selenium for browser automation (handles ASP.NET ViewState + JavaScript)
    2. TrOCR-based CAPTCHA solving
    3. Rate-limited requests (2-4 second delays)
    4. Checkpoint-based progress saving
    5. Retry logic for failed CAPTCHAs

Dependencies:
    - selenium + webdriver-manager (auto-downloads ChromeDriver)
    - captcha_model (TrOCR solver)
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
# pyrefly: ignore [missing-import]
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


# 
# Configuration
# 

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


# 
# Selenium WebDriver Setup
# 

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


# 
# CAPTCHA Handling
# 

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
        captcha_element = None
        
        # Method 1: Alt text
        try:
            captcha_element = driver.find_element(By.XPATH, "//img[@alt='Captcha']")
        except NoSuchElementException:
            pass
            
        # Method 2: Src containing CaptchaImage
        if captcha_element is None:
            try:
                captcha_element = driver.find_element(By.XPATH, "//img[contains(@src, 'CaptchaImage')]")
            except NoSuchElementException:
                pass
                
        # Method 3: Common IDs
        if captcha_element is None:
            captcha_selectors = ["imgCaptcha", "CaptchaImage", "imgVarification"]
            for sel in captcha_selectors:
                try:
                    captcha_element = driver.find_element(By.ID, sel)
                    break
                except NoSuchElementException:
                    continue

        if captcha_element is None:
            raise RuntimeError("Could not find CAPTCHA image element on page")

        # Wait for image to fully load
        driver.execute_script("""
            var img = arguments[0];
            if (!img.complete) {
                return new Promise(resolve => { img.onload = resolve; });
            }
        """, captcha_element)
        time.sleep(0.3)

        # Extract actual image bytes via JS canvas (NOT screenshot)
        b64_data = driver.execute_script("""
            var img = arguments[0];
            var canvas = document.createElement('canvas');
            canvas.width = img.naturalWidth || img.width;
            canvas.height = img.naturalHeight || img.height;
            var ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            return canvas.toDataURL('image/png').split(',')[1];
        """, captcha_element)
        
        import base64
        png_bytes = base64.b64decode(b64_data)
        captcha_img = Image.open(BytesIO(png_bytes))

        # Save for training data collection (optional)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            save_path = os.path.join(save_dir, f"captcha_{timestamp}.png")
            captcha_img.save(save_path)

        return captcha_img

    except Exception as e:
        print(f"   Error downloading CAPTCHA: {e}")
        return None


# 
# Result Parsing
# 

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

        # Check for error messages
        page_text = soup.get_text().lower()
        if 'incorrect' in page_text and 'result' not in page_text[:100].lower():
             return None

        result_data = {}

        # 1. Top Section (Name, Roll, Branch, etc)
        spans = soup.find_all("span")
        for s in spans:
            id_attr = s.get("id", "").lower()
            text = s.get_text(strip=True)
            if "lblname" in id_attr or "lblstudentname" in id_attr:
                result_data['student_name'] = text
            if "lblroll" in id_attr or "lblenrol" in id_attr:
                result_data['enrollment'] = text
            if "lblbranch" in id_attr:
                result_data['branch'] = text
            if "lblsem" in id_attr:
                result_data['semester'] = text
            if "lblcourse" in id_attr:
                result_data['program'] = text
            if "lblstatus" in id_attr:
                result_data['status'] = text

        # 2. Extract Tables
        tables = soup.find_all("table")
        subjects = []
        for t in tables:
            rows = t.find_all("tr")
            if not rows: continue
            
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
            
            # Subject Table
            if "course code" in headers or "grade" in headers:
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) >= 4:
                        subjects.append({
                            'course_code': cells[0],
                            'total_credit': cells[1],
                            'earned_credit': cells[2],
                            'grade': cells[3]
                        })
                        
            # Footer Table (Result, SGPA, CGPA)
            elif "result des." in headers or "sgpa" in headers:
                if len(rows) > 1:
                    cells = [td.get_text(strip=True) for td in rows[1].find_all('td')]
                    if len(cells) >= 3:
                        result_data['result_status'] = cells[0]
                        result_data['sgpa'] = cells[1]
                        result_data['cgpa'] = cells[2]

        if subjects:
            result_data['subjects'] = subjects

        return result_data if result_data else None

    except Exception as e:
        print(f"   Error parsing result: {e}")
        return None


# 
# Main Scraper
# 

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
            # Navigate to program select
            driver.get(PROGRAM_SELECT_URL)
            time.sleep(1)
            
            # Click the radio button for the specific program (e.g. B.Tech)
            # This is CRITICAL to initialize the ASP.NET Session properly
            try:
                rbs = driver.find_elements(By.XPATH, "//input[@type='radio']")
                for rb in rbs:
                    if 'BTech' in rb.get_attribute('id') or 'B.Tech' in rb.find_element(By.XPATH, '..').text:
                        rb.click()
                        break
            except Exception as e:
                print(f"    Warning: Could not select program radio button: {e}")
            
            time.sleep(2) # Wait for redirect to Result_BTech.aspx

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
                semester_dropdown = None
                dropdown_selectors = ["ddlSemester", "ddlsem", "ddl_semester"]
                for sel in dropdown_selectors:
                    try:
                        semester_dropdown = driver.find_element(By.ID, sel)
                        break
                    except NoSuchElementException:
                        pass
                
                if semester_dropdown is None:
                    # Fallback to finding the first select element
                    selects = driver.find_elements(By.TAG_NAME, "select")
                    if selects:
                        semester_dropdown = selects[0]
                
                if semester_dropdown:
                    select = Select(semester_dropdown)
                    # Use provided semester
                    select.select_by_value(str(semester))
            except Exception as e:
                print(f"    Warning: Could not select semester {semester}: {e}")
            
            time.sleep(2) # Wait for PostBack after semester selection
            
            # Find CAPTCHA image element
            captcha_element = None
            
            # Method 1: Alt text
            try:
                captcha_element = driver.find_element(By.XPATH, "//img[@alt='Captcha']")
            except NoSuchElementException:
                pass
                
            # Method 2: Src containing CaptchaImage
            if captcha_element is None:
                try:
                    captcha_element = driver.find_element(By.XPATH, "//img[contains(@src, 'CaptchaImage')]")
                except NoSuchElementException:
                    pass

            # Method 3: Common IDs
            if captcha_element is None:
                captcha_selectors = ["imgCaptcha", "CaptchaImage", "imgVarification"]
                for sel in captcha_selectors:
                    try:
                        captcha_element = driver.find_element(By.ID, sel)
                        break
                    except NoSuchElementException:
                        continue

            if captcha_element is None:
                raise RuntimeError("Could not find CAPTCHA image element on page")

            # CRITICAL: Force CAPTCHA image to reload!
            # The semester dropdown triggers an ASP.NET PostBack which generates a new CAPTCHA on the server.
            # But the browser caches the old image since the URL doesn't change. We must force a refresh.
            driver.execute_script("arguments[0].src = arguments[0].src + '&t=' + new Date().getTime();", captcha_element)
            time.sleep(1) # wait for new image to load

            # Wait for image to fully load
            driver.execute_script("""
                var img = arguments[0];
                if (!img.complete) {
                    return new Promise(resolve => { img.onload = resolve; });
                }
            """, captcha_element)

            # Download and solve CAPTCHA
            captcha_img = download_captcha_image(driver, captcha_save_dir)
            if captcha_img is None:
                print(f"    Could not download CAPTCHA (attempt {attempt+1})")
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

            # Scroll into view and click (handling overlapping footer)
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.2)
            try:
                submit_btn.click()
            except Exception:
                # Fallback if covered by footer
                driver.execute_script("arguments[0].click();", submit_btn)

            # Wait for result page to load
            time.sleep(2)

            # Check for JS alerts (e.g., "you have entered a wrong text")
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text.lower()
                alert.accept()
                if 'wrong' in alert_text or 'incorrect' in alert_text:
                    print(f"    Wrong CAPTCHA (alert) (attempt {attempt+1}/{MAX_CAPTCHA_RETRIES})")
                    continue
            except Exception:
                pass

            # Check for CAPTCHA error (wrong CAPTCHA  page reloads)
            page_text = driver.page_source.lower()
            if 'incorrect' in page_text or 'wrong' in page_text:
                print(f"    Wrong CAPTCHA (attempt {attempt+1}/{MAX_CAPTCHA_RETRIES})")
                continue

            # Parse results
            result = parse_result_page(driver)
            if result is not None:
                result['enrollment'] = enrollment_no
                result['semester'] = str(semester)
                return result
            else:
                print(f"    No result found for {enrollment_no}")
                return {'enrollment': enrollment_no, 'semester': str(semester),
                        'result_status': 'NOT_FOUND'}

        except TimeoutException:
            print(f"    Timeout (attempt {attempt+1})")
            continue
        except Exception as e:
            print(f"   Error: {e} (attempt {attempt+1})")
            continue

    print(f"   Failed all {MAX_CAPTCHA_RETRIES} attempts for {enrollment_no}")
    return {'enrollment': enrollment_no, 'semester': str(semester),
            'result_status': 'SCRAPE_FAILED'}


# 
# Checkpoint Management
# 

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


# 
# Main Scrape Pipeline
# 

def run_scraper(model_path=None, headless=True, save_captchas=True,
                branch_filter=None, resume=True):
    """
    Run the full scraping pipeline for all students.

    Args:
        model_path: Path to trained CAPTCHA TrOCR model.
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
    print("\n Loading CAPTCHA solver...")
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
    print(f"\n Students to scrape: {total}")

    # Resume from checkpoint
    results = []
    scraped_enrollments = set()
    if resume:
        results = load_checkpoint(checkpoint_path)
        scraped_enrollments = {r.get('enrollment') for r in results}
        if scraped_enrollments:
            print(f" Resuming from checkpoint: {len(scraped_enrollments)} already scraped")

    # Create WebDriver
    print("\n Starting browser...")
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
        print("\n\n  Scraping interrupted by user. Saving progress...")
        save_checkpoint(results, checkpoint_path)
    except Exception as e:
        print(f"\n Fatal error: {e}")
        save_checkpoint(results, checkpoint_path)
        raise
    finally:
        driver.quit()
        print(" Browser closed.")

    # Save raw results
    raw_path = os.path.join(raw_dir, f'raw_results_{SEMESTER}.json')
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n Raw results saved to: {raw_path}")

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
