import os
import logging
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from robocorp.tasks import task
from robocorp import browser
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = os.getenv("AMD_URL")

def open_login_page():
    browser.configure(
        slowmo=3000,
        headless=False,
        browser_engine="chromium"
    )
    browser.goto(LOGIN_URL)
    browser.page().set_viewport_size({"width":1920,"height":1080})

def get_user_credentials():
    username = os.getenv("AMD_USERNAME")
    password = os.getenv("AMD_PASSWORD")
    office_key = os.getenv("AMD_OFFICEKEY")

    if not username or not password or not office_key:
        assistant = Assistant()
        assistant.add_heading("AdvancedMD Login Required")
        assistant.add_text_input("username", placeholder="Enter your username")
        assistant.add_password_input("password", placeholder="Enter your password")
        assistant.add_text_input("office_key", placeholder="Enter the client office key")
        assistant.add_submit_buttons(buttons=["Login"], default="Login")
        result = assistant.run_dialog()
        username = result.email
        password = result.password
        office_key = result.office_key

    return username, password, office_key


def fill_login(username=None, password=None, office_key=None):
    if not username or not password or not office_key:
        username, password, office_key = get_user_credentials()

    page = browser.page()

    # Make sure basic DOM is loaded
    page.wait_for_load_state("domcontentloaded")

    login_context = None

    try:
        page.wait_for_selector("#loginName", timeout=8000)
        login_context = page
    except Exception:
        for frame in page.frames:
            try:
                frame.wait_for_selector("#loginName", timeout=5000)
                login_context = frame
                break
            except Exception:
                continue

    if login_context is None:
        raise RuntimeError("Could not find AdvancedMD login form (input#loginName) in any frame.")

    # Fill the fields
    login_context.fill("#loginName", username)
    login_context.fill("#password", password)
    login_context.fill("#officeKey", office_key)
    
    # Submit info
    try:
        login_context.click("button[type='submit']")
    except Exception:
        try:
            login_context.get_by_role("button", name="Login").click()
        except Exception:
            logging.warning("Login button not found; fields were filled but not submitted.")




@task
def alexandria_report_automation():
    open_login_page()
    username, password, office_key = get_user_credentials()
    fill_login(username, password, office_key)