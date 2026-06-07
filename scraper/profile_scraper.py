"""
MITS Gwalior Student Profile Scraper (Add-on)
=============================================
This script logs into the MITS portal using a specific student's 
credentials, solves the CAPTCHA, and extracts data from the 
protected Student Profile page.

Usage:
    python profile_scraper.py --enrollment BTAD24O1063 --password "YourPassword"
"""

import os
import sys
import time
import json
import argparse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.scraper import create_driver, download_captcha_image
from captcha_model.predict import CaptchaSolver

LOGIN_URL = "https://iums.mitsgwalior.in/Login/StudentLogin.aspx"
PROFILE_URL = "https://iums.mitsgwalior.in/StudentLife/Student_UploadPhoto.aspx?url=Student%20Profile"

def login_and_scrape_profile(driver, solver, enrollment, password):
    print(f"\n[1] Navigating to Login Page: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    time.sleep(2)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"\n--- Login Attempt {attempt+1}/{max_retries} ---")
            
            # Fill Username (Enrollment)
            user_input = None
            for sel in ["txtUser", "txtEnrollmentNo", "txt_enrollment"]:
                try:
                    user_input = driver.find_element(By.ID, sel)
                    break
                except:
                    pass
            if not user_input:
                user_input = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
            
            user_input.clear()
            user_input.send_keys(enrollment)
            
            # Fill Password
            pass_input = None
            for sel in ["txtPassword", "txtPass"]:
                try:
                    pass_input = driver.find_element(By.ID, sel)
                    break
                except:
                    pass
            if not pass_input:
                pass_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                
            pass_input.clear()
            pass_input.send_keys(password)
            
            # Get CAPTCHA image and solve
            print("Downloading CAPTCHA...")
            captcha_img = download_captcha_image(driver)
            if captcha_img is None:
                print("Failed to get CAPTCHA image, retrying...")
                driver.refresh()
                time.sleep(2)
                continue
                
            captcha_text, conf = solver.solve(captcha_img)
            print(f"Solved CAPTCHA: '{captcha_text}' (conf: {conf:.2f})")
            
            # Fill CAPTCHA
            captcha_input = None
            for sel in ["txtCaptcha", "txtVerification", "txtVarification"]:
                try:
                    captcha_input = driver.find_element(By.ID, sel)
                    break
                except:
                    pass
            if not captcha_input:
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                captcha_input = inputs[-1]
                
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)
            
            # Click Login
            login_btn = None
            for sel in ["btnLogin", "btnSubmit", "Button1"]:
                try:
                    login_btn = driver.find_element(By.ID, sel)
                    break
                except:
                    pass
            if not login_btn:
                login_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                
            driver.execute_script("arguments[0].click();", login_btn)
            time.sleep(3)
            
            # Check if login failed
            page_text = driver.page_source.lower()
            if "incorrect" in page_text or "wrong" in page_text or "invalid" in page_text:
                print("Login failed (Invalid credentials or wrong CAPTCHA).")
                continue
                
            print("Login successful!")
            break
            
        except Exception as e:
            print(f"Error during login: {e}")
            time.sleep(2)
            
    else:
        print("Max retries reached. Could not log in.")
        return None

    # Step 2: Navigate to Profile Page
    print(f"\n[2] Navigating to Profile Page: {PROFILE_URL}")
    driver.get(PROFILE_URL)
    time.sleep(3)
    
    # Parse the profile page
    print("\n[3] Extracting Profile Data...")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    profile_data = {'enrollment': enrollment}
    
    # Handle standard span texts (readonly labels)
    for s in soup.find_all("span"):
        id_attr = s.get("id", "").lower()
        text = s.get_text(strip=True)
        if "lblname" in id_attr or "lblstudentname" in id_attr: profile_data['name'] = text
        elif "lblayear" in id_attr: profile_data['admission_year'] = text
        elif "lblinstitute" in id_attr: profile_data['institute'] = text
        elif "lblprogram" in id_attr: profile_data['program'] = text
        elif "lblbranch" in id_attr: profile_data['branch'] = text

    # Handle inputs (texts, dates, etc.)
    for i in soup.find_all("input"):
        id_attr = i.get("id", "").lower()
        val = i.get("value", "").strip()
        if not val: continue
        if "txtfname" in id_attr: profile_data['father_name'] = val
        elif "txtmother" in id_attr: profile_data['mother_name'] = val
        elif "txtdob" in id_attr: profile_data['dob'] = val
        elif "txtmobile" in id_attr: profile_data['mobile'] = val
        elif "txtemail" in id_attr: profile_data['email'] = val
        elif "txtabcid" in id_attr: profile_data['abc_id'] = val

    # Handle textareas (Address)
    for t in soup.find_all("textarea"):
        if "txtaddress" in t.get("id", "").lower():
            profile_data['address'] = t.get_text(strip=True)

    # Handle selects (Gender, Blood Group, Religion)
    for s in soup.find_all("select"):
        id_attr = s.get("id", "").lower()
        selected_option = s.find("option", selected=True)
        if selected_option:
            val = selected_option.get_text(strip=True)
            if "drpgender" in id_attr: profile_data['gender'] = val
            elif "drpbg" in id_attr: profile_data['blood_group'] = val
            elif "drpreligion" in id_attr: profile_data['religion'] = val

    print("\n[4] Navigating to Academic History...")
    # To reach Academic History, we must go through Student Services dashboard
    driver.get("https://iums.mitsgwalior.in/StudentLife/Studenthome.aspx")
    time.sleep(2)
    
    academic_history_data = []
    try:
        # Try to find and click the Academic History link
        academic_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Academic")
        academic_link.click()
        time.sleep(3)
        
        ac_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Scrape academic history tables
        tables = ac_soup.find_all("table")
        for t in tables:
            rows = t.find_all("tr")
            if not rows: continue
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
            
            if "sgpa" in headers or "cgpa" in headers or "semester" in headers:
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) >= 3:
                        academic_history_data.append(cells)
        
        profile_data['academic_history'] = academic_history_data
        print(f"Extracted {len(academic_history_data)} academic records.")
    except Exception as e:
        print(f"Could not extract Academic History: {e}")

    print("\nExtraction Complete! Data found:")
    print(json.dumps(profile_data, indent=2))
    
    # Save to file
    out_dir = os.path.join(project_root, 'data', 'profiles')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"profile_{enrollment}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2)
    print(f"\nSaved profile data to: {out_path}")
    
    return profile_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MITS Student Profile Scraper")
    parser.add_argument('--enrollment', type=str, required=True, help="Student Enrollment Number")
    parser.add_argument('--password', type=str, required=True, help="Student Portal Password")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    args = parser.parse_args()

    print("Loading TrOCR CAPTCHA model...")
    solver = CaptchaSolver()
    
    print("Starting browser...")
    driver = create_driver(headless=args.headless)
    
    try:
        login_and_scrape_profile(driver, solver, args.enrollment, args.password)
    finally:
        driver.quit()
        print("Browser closed.")
