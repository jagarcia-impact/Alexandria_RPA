import os
import logging
import time
from datetime import datetime
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

def snooze_all_notifications():
    """
    If a 'Snooze all' notification button is visible after login,
    click it. If it's not there, just continue without failing.
    """
    page = browser.page()

    page.wait_for_load_state("domcontentloaded")

    try:
        btn = page.get_by_role("button", name="Snooze all")
        btn.wait_for(state="visible", timeout=3000)
        btn.click()
        logging.info("Clicked 'Snooze all' on main page.")
        return
    except Exception:
        pass

    for frame in page.frames:
        try:
            btn = frame.get_by_role("button", name="Snooze all")
            btn.wait_for(state="visible", timeout=3000)
            btn.click()
            logging.info("Clicked 'Snooze all' inside a frame.")
            return
        except Exception:
            continue

    logging.info("'Snooze all' button not found; continuing without snoozing.")

def get_main_app_page():
    """
    Find the AdvancedMD main app page by looking for
    <a class="dropdown-toggle">Reports</a> in the DOM.
    """
    current_page = browser.page()
    current_page.wait_for_load_state("domcontentloaded")

    def page_has_reports(page_obj, timeout=4000):
        try:
            contexts = [page_obj] + list(page_obj.frames)
            for ctx in contexts:
                try:
                    locator = ctx.locator("a.dropdown-toggle", has_text="Reports").first
                    locator.wait_for(state="visible", timeout=timeout)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    if page_has_reports(current_page, timeout=3000):
        logging.info(f"Using current page as main app page (URL: {current_page.url})")
        return current_page

    context = current_page.context
    deadline = time.time() + 5

    while time.time() < deadline:
        for p in context.pages:
            try:
                p.wait_for_load_state("domcontentloaded")
            except Exception:
                continue

            if page_has_reports(p, timeout=2500):
                p.bring_to_front()
                logging.info(f"Using main app page with URL: {p.url}")
                return p

        time.sleep(1)

    raise RuntimeError("Could not find the AdvancedMD main app page (no 'Reports' dropdown-toggle found).")

def click_reports_menu(main_page):
    main_page.bring_to_front()
    main_page.wait_for_load_state("domcontentloaded")

    contexts = [main_page] + list(main_page.frames)

    for ctx in contexts:
        try:
            locator = ctx.locator("a.dropdown-toggle", has_text="Reports").first
            locator.wait_for(state="visible", timeout=2500)
            locator.click()
            logging.info("Clicked 'Reports' menu.")
            return
        except Exception:
            continue

    raise RuntimeError("Could not find the 'Reports' menu (a.dropdown-toggle with text 'Reports').")

def run_end_of_day_totals(main_page):
    """
    Open Reports -> Financial Totals -> End of Day Totals
    and handle the popup window.
    """
    main_page.wait_for_load_state("domcontentloaded")
    main_page.bring_to_front()

    # 2) Hover/click "Financial Totals" so its submenu appears
    fin_totals = main_page.locator("a", has_text="Financial Totals").first
    fin_totals.wait_for(state="visible", timeout=2500)
    fin_totals.hover()
    # small pause so the third-level menu renders
    main_page.wait_for_timeout(500)

    with main_page.expect_popup() as eod_popup_info:
        eod_link = main_page.locator("a", has_text="End of Day Totals").first
        eod_link.wait_for(state="visible", timeout=2500)
        eod_link.click()

    # 4) Work in the popup
    eod_page = eod_popup_info.value
    eod_page.wait_for_load_state("domcontentloaded")

    download_dir = os.path.join(os.getcwd(), "output", "downloads")
    os.makedirs(download_dir, exist_ok=True)

    eod_page.click("#\\32 236 .col-xs-12")
    with eod_page.expect_download() as download_info:
        eod_page.click(".fixed")

    run_dt = datetime.now()
    month_start = run_dt.replace(day=1)
    download = download_info.value
    original_filename = download.suggested_filename
    _, ext = os.path.splitext(original_filename)
    new_filename = (
        f"endofdaytotals_{month_start.strftime('%Y%m%d')}_"
        f"{run_dt.strftime('%Y%m%d')}{ext}"
    )
    target_path = os.path.join(download_dir, new_filename)
    download.save_as(target_path)
    logging.info(f"End of Day Totals report downloaded to: {target_path}")

    # 5) Close pop-up
    try:
        eod_page.click(".btn:nth-child(1)")  # Close /

    except Exception:
        logging.warning("Could not click close button on End of Day Totals popup.")

    try:
        eod_page.close()
    except Exception:
        pass

    return target_path

def run_transaction_detail(main_page):
    """
    Open Reports -> Financial Totals -> Transaction Detail,
    trigger the report download, save the file, and close the popup.
    """
    main_page.wait_for_load_state("domcontentloaded")
    main_page.bring_to_front()

    # Assumes Reports menu is already open (click_reports_menu was just called)

    # 1) Hover "Financial Totals" so its submenu appears
    fin_totals = main_page.locator("a", has_text="Financial Totals").first
    fin_totals.wait_for(state="visible", timeout=2500)
    fin_totals.hover()
    main_page.wait_for_timeout(500)

    # 2) Click "Transaction Detail" (opens popup)
    with main_page.expect_popup() as tx_popup_info:
        tx_link = main_page.locator("a", has_text="Transaction Detail").first
        tx_link.wait_for(state="visible", timeout=2500)
        tx_link.click()

    # 3) Work in the popup
    tx_page = tx_popup_info.value
    tx_page.wait_for_load_state("domcontentloaded")

    download_dir = os.path.join(os.getcwd(), "output", "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Select the report option (id 2237, analogous to 2236 above)
    tx_page.click("#\\32 237 .col-xs-12")

    # 4) Click the "Run report" button, which should trigger the download
    with tx_page.expect_download() as download_info:
        tx_page.click(".run-report")

    download = download_info.value
    original_filename = download.suggested_filename
    run_dt = datetime.now()
    month_start = run_dt.replace(day=1)
    _, ext = os.path.splitext(original_filename)
    new_filename = (
        f"transactiondetail_{month_start.strftime('%Y%m%d')}_"
        f"{run_dt.strftime('%Y%m%d')}{ext}"
    )
    target_path = os.path.join(download_dir, new_filename)
    download.save_as(target_path)
    logging.info(f"Transaction Detail report downloaded to: {target_path}")

    # 5) Close the popup AFTER download
    try:
        tx_page.click(".btn:nth-child(1)")  # Close / OK
    except Exception:
        logging.warning("Could not click close button on Transaction Detail popup.")

    try:
        tx_page.close()
    except Exception:
        pass

    return target_path

@task
def alexandria_report_automation():
    open_login_page()
    username, password, office_key = get_user_credentials()
    fill_login(username, password, office_key)
    snooze_all_notifications()
    main_page = get_main_app_page()
    click_reports_menu(main_page)
    eod_path = run_end_of_day_totals(main_page)
    logging.info(f"EOD totals report saved at {eod_path}")
    click_reports_menu(main_page)
    trx_path = run_transaction_detail(main_page)
    logging.info(f"Transaction detail report saved at {trx_path}")
