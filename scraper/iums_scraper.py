"""
IUMS Portal Scraper
====================
Scrapes student details, fee, and academic history from the IUMS portal:
https://iums.mitsgwalior.in/

Dependencies:
    - selenium
    - beautifulsoup4
    - pandas
"""

import os
import sys
import time
import json
import csv
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.scraper import create_driver, download_captcha_image
from captcha_model.predict import CaptchaSolver

# Configuration
IUMS_HOME_URL = "https://iums.mitsgwalior.in/"
PAGE_LOAD_TIMEOUT = 15
MAX_CAPTCHA_RETRIES = 5

def login_to_iums(driver, enrollment, password, captcha_solver):
    """
    Log into the IUMS portal via the homepage to maintain ASP.NET session state.
    """
    for attempt in range(MAX_CAPTCHA_RETRIES):
        print(f"  Attempting login for {enrollment} (Attempt {attempt+1})")
        driver.get(IUMS_HOME_URL)
        time.sleep(2)
        
        # 1. Click "Student Login" link
        try:
            # Look for link containing 'StudentLogin.aspx' or text 'Student Login'
            login_link = driver.find_element(By.XPATH, "//a[contains(@href, 'StudentLogin.aspx') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'student login')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", login_link)
            time.sleep(0.5)
            # Use JavaScript click to bypass the 'onload' modal popup blocking the element
            driver.execute_script("arguments[0].click();", login_link)
        except NoSuchElementException:
            print("   Error: Could not find 'Student Login' link on homepage.")
            return False

        time.sleep(2)

        # 2. Find inputs (Enrollment, Password)
        try:
            # Find all visible text inputs
            text_inputs = [inp for inp in driver.find_elements(By.XPATH, "//input[@type='text' or not(@type)]") if inp.is_displayed() and not inp.get_attribute('readonly') and not inp.get_attribute('disabled')]
            
            if len(text_inputs) >= 2:
                user_input = text_inputs[0]
            elif len(text_inputs) == 1:
                user_input = text_inputs[0]
            else:
                user_input = None

            pass_input = None
            pass_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
            if pass_inputs:
                pass_input = pass_inputs[0]

            if not user_input or not pass_input:
                raise RuntimeError(f"Could not find username ({len(text_inputs)} text inputs) or password inputs")
                
            user_input.clear()
            user_input.send_keys(enrollment)
            pass_input.clear()
            pass_input.send_keys(password)
            
        except Exception as e:
            print(f"   Error filling credentials: {e}")
            return False

        # 3. Solve CAPTCHA
        captcha_img = download_captcha_image(driver)
        if captcha_img is None:
            print("   Failed to download CAPTCHA.")
            continue
            
        captcha_text, confidence = captcha_solver.solve(captcha_img)
        print(f"   Solved CAPTCHA: {captcha_text} (conf: {confidence:.3f})")
        
        try:
            captcha_input = None
            
            # The CAPTCHA input is typically the last visible text input
            if len(text_inputs) >= 2:
                captcha_input = text_inputs[-1]
            else:
                for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                    if inp != user_input and inp.is_displayed():
                        captcha_input = inp
            
            if not captcha_input:
                raise RuntimeError("Could not find CAPTCHA input")
                
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)
            
            # Click Login Button
            submit_btn = None
            buttons = driver.find_elements(By.TAG_NAME, 'input')
            for btn in buttons:
                b_type = (btn.get_attribute('type') or '').lower()
                b_val = (btn.get_attribute('value') or '').lower()
                if b_type == 'submit' or 'login' in b_val or 'sign' in b_val:
                    submit_btn = btn
                    break
                    
            if not submit_btn:
                # Try finding button tag
                buttons = driver.find_elements(By.TAG_NAME, 'button')
                for btn in buttons:
                    if 'login' in btn.text.lower():
                        submit_btn = btn
                        break
                        
            driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(3)
            
            # Check for error alert or text
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text.lower()
                alert.accept()
                if 'wrong' in alert_text or 'incorrect' in alert_text or 'captcha' in alert_text:
                    print("   Incorrect CAPTCHA or credentials.")
                    continue
            except:
                pass
                
            page_text = driver.page_source.lower()
            if 'incorrect' in page_text or 'wrong' in page_text or 'invalid' in page_text:
                print("   Login failed (incorrect credentials or captcha).")
                continue
                
            # If we reached here without errors, we are logged in!
            print("   Login successful!")
            return True
            
        except Exception as e:
            print(f"   Login process error: {e}")
            continue

    return False

def click_menu_item(driver, text):
    """Utility to click a menu item by text, prioritizing elements on the left sidebar."""
    try:
        # Use '.' to match text inside nested tags (like spans or icons inside the anchor)
        xpath = f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
        items = driver.find_elements(By.XPATH, xpath)
        
        displayed_items = [item for item in items if item.is_displayed()]
        if not displayed_items:
            return False
            
        target = None
        # Prioritize items on the left side of the screen (sidebar) to avoid top-right header menus
        for item in displayed_items:
            if item.location['x'] < 400:
                target = item
                break
                
        if target is None:
            target = displayed_items[0]
            
        driver.execute_script("arguments[0].click();", target)
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"   Error clicking menu '{text}': {e}")
        return False

def extract_semester_fee_and_profile(driver):
    """Extract semester fee data and student profile from the Semester Registration page"""
    print("   Navigating to Semester Fees Submission Form...")
    click_menu_item(driver, "semester fees")
        
    if not click_menu_item(driver, "semester fees submission form") and not click_menu_item(driver, "semester fee submission"):
        print("   Could not navigate to Semester Fee Submission form.")
        return {}, {}
        
    time.sleep(2)
    
    # Click the Search button
    try:
        search_btn = driver.find_element(By.XPATH, "//*[contains(translate(@value, 'SEARCH', 'search'), 'search') or contains(translate(text(), 'SEARCH', 'search'), 'search')]")
        driver.execute_script("arguments[0].click();", search_btn)
        time.sleep(3)
    except Exception as e:
        print(f"   Warning: Could not click Search button: {e}")
        
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    fee_data = {}
    profile_data = {}
    
    tables = soup.find_all("table")
    for t in tables:
        rows = t.find_all("tr")
        if not rows: continue
        
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        
        # Check if it's the Admission Renewal table
        if any("admission status" in h for h in headers) or any("academic year" in h for h in headers):
            # Extract fee status for each semester
            # Example headers: Select, Enrollment No., Academic Year, Year/Semester, Admission Status
            sem_idx = -1
            status_idx = -1
            year_idx = -1
            for i, h in enumerate(headers):
                if "semester" in h or "sem" in h: sem_idx = i
                if "status" in h: status_idx = i
                if "academic year" in h or "year" in h: year_idx = i
                
            if sem_idx != -1 and status_idx != -1:
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) > max(sem_idx, status_idx):
                        sem_val = cells[sem_idx].strip()
                        status_val = cells[status_idx].strip()
                        if sem_val:
                            fee_data[f"fee_{sem_val}_status"] = status_val
                            if year_idx != -1 and len(cells) > year_idx:
                                fee_data[f"fee_{sem_val}_year"] = cells[year_idx].strip()
                            
        # Otherwise, process as a profile key-value table
        else:
            for row in rows:
                cells = [td.get_text(separator=" ", strip=True) for td in row.find_all(['th', 'td'])]
                for i in range(len(cells) - 1):
                    cell_lower = cells[i].lower()
                    val = cells[i+1]
                    if not val: continue
                    
                    if "name" in cell_lower and "father" not in cell_lower and "mother" not in cell_lower and "institute" not in cell_lower:
                        profile_data["profile_name"] = val
                    elif "father" in cell_lower:
                        profile_data["profile_father"] = val
                    elif "mother" in cell_lower:
                        profile_data["profile_mother"] = val
                    elif "gender" in cell_lower:
                        profile_data["profile_gender"] = val
                    elif "dob" in cell_lower or "date of birth" in cell_lower:
                        profile_data["profile_dob"] = val
                    elif "category" in cell_lower:
                        profile_data["profile_category"] = val
                    elif "area" in cell_lower:
                        profile_data["profile_area"] = val
                    elif "programme" in cell_lower or "course" in cell_lower:
                        profile_data["profile_programme"] = val
                    elif "branch" in cell_lower:
                        profile_data["profile_branch"] = val
                    elif "mobile" in cell_lower or "phone" in cell_lower:
                        profile_data["profile_phone"] = val
                    elif "mail" in cell_lower:
                        profile_data["profile_email"] = val
                    elif "permanent address" in cell_lower:
                        profile_data["profile_address"] = val
                    elif "city" in cell_lower:
                        profile_data["profile_city"] = val
                    elif "state" in cell_lower:
                        profile_data["profile_state"] = val
                    elif "pincode" in cell_lower:
                        profile_data["profile_pincode"] = val
                    elif "admission year" in cell_lower:
                        profile_data["profile_admission_year"] = val
                        
    return fee_data, profile_data



def extract_academic_history(driver):
    """Extract SGPA and compute CGPA"""
    print("   Navigating to Academic History...")
    # First expand Student Profile menu if it's not expanded
    click_menu_item(driver, "student profile")
    time.sleep(1)
    
    if not click_menu_item(driver, "academic history"):
        print("   Could not navigate to Academic History.")
        return {}
        
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    data = {}
    sgpa_list = []
    
    tables = soup.find_all("table")
    for t in tables:
        rows = t.find_all("tr")
        if not rows: continue
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        
        # Look for a table that has SGPA
        if any("sgpa" in h for h in headers):
            sgpa_idx = -1
            sem_idx = -1
            session_idx = -1
            result_idx = -1
            for i, h in enumerate(headers):
                if "sgpa" in h: sgpa_idx = i
                if "sem" in h: sem_idx = i
                if "session" in h: session_idx = i
                if "result" in h: result_idx = i
                
            if sgpa_idx != -1:
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) > sgpa_idx:
                        sgpa_val = cells[sgpa_idx].strip()
                        sem_val = cells[sem_idx].strip() if sem_idx != -1 and len(cells) > sem_idx else f"{len(sgpa_list)+1}"
                        try:
                            sgpa_float = float(sgpa_val)
                            sgpa_list.append(sgpa_float)
                            data[f"sem_{sem_val}_sgpa"] = sgpa_float
                            
                            if session_idx != -1 and len(cells) > session_idx:
                                data[f"sem_{sem_val}_session"] = cells[session_idx].strip()
                            if result_idx != -1 and len(cells) > result_idx:
                                data[f"sem_{sem_val}_result"] = cells[result_idx].strip()
                        except ValueError:
                            pass
                            
    if sgpa_list:
        data["overall_cgpa"] = sum(sgpa_list) / len(sgpa_list)
        
    return data

def save_data(all_data, data_dir):
    """Save the collected data into separate CSV files."""
    os.makedirs(data_dir, exist_ok=True)
    
    fee_data = []
    profile_data = []
    academic_data = []
    
    for d in all_data:
        base_info = {'enrollment': d['enrollment']}
        
        f_row = base_info.copy()
        f_row.update(d.get('fee', {}))
        fee_data.append(f_row)
        
        p_row = base_info.copy()
        p_row.update(d.get('profile', {}))
        profile_data.append(p_row)
        
        a_row = base_info.copy()
        a_row.update(d.get('academic', {}))
        academic_data.append(a_row)
        
    if fee_data:
        pd.DataFrame(fee_data).to_csv(os.path.join(data_dir, 'iums_fee.csv'), index=False)
    if profile_data:
        pd.DataFrame(profile_data).to_csv(os.path.join(data_dir, 'iums_profile.csv'), index=False)
    if academic_data:
        pd.DataFrame(academic_data).to_csv(os.path.join(data_dir, 'iums_academic.csv'), index=False)
        
    print(f"\n Data saved to {data_dir}/iums_*.csv")

def run_iums_scraper(credentials_list, model_path=None, headless=True):
    """
    Run the IUMS scraping pipeline for a list of credentials.
    credentials_list: List of dicts [{'enrollment': '...', 'password': '...'}, ...]
    """
    print("=" * 60)
    print("IUMS Portal Scraper")
    print("=" * 60)
    
    solver = CaptchaSolver(model_path=model_path)
    driver = create_driver(headless=headless)
    
    all_data = []
    
    try:
        for creds in tqdm(credentials_list, desc="Scraping IUMS"):
            enrollment = creds['enrollment']
            password = creds['password']
            
            success = login_to_iums(driver, enrollment, password, solver)
            if not success:
                print(f"  Skipping {enrollment} due to login failure.")
                continue
                
            student_data = {'enrollment': enrollment}
            
            # CRITICAL: Expand the main "Student Services" sidebar menu first!
            print("   Expanding main Student Services menu...")
            click_menu_item(driver, "student services")
            time.sleep(2)
            
            # Extract data
            fee_data, profile_data = extract_semester_fee_and_profile(driver)
            student_data['fee'] = fee_data
            student_data['profile'] = profile_data
            
            student_data['academic'] = extract_academic_history(driver)
            
            all_data.append(student_data)
            
            # Logout logic (optional, but good practice to clear session)
            click_menu_item(driver, "logout")
            time.sleep(1)
            
    except Exception as e:
        print(f"Fatal error during IUMS scraping: {e}")
    finally:
        driver.quit()
        
    # Save extracted data
    data_dir = os.path.join(project_root, 'data')
    save_data(all_data, data_dir)
    return all_data
