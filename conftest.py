"""Trình duyệt riêng cho từng test; lưu bằng chứng và kết quả thực tế."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import pytest_html
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from pages.store import Store

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", help="Hiện cửa sổ Chrome")
    parser.addoption("--base-url", default="https://www.saucedemo.com/",
                     help="URL gốc của SauceDemo")


def pytest_configure(config):
    (REPORTS / "screenshots").mkdir(parents=True, exist_ok=True)
    config._selenium_results = []
    config._selenium_started = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()


@pytest.fixture
def driver(request):
    options = Options()
    if not request.config.getoption("--headed"):
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-dev-shm-usage")
    if os.name != "nt" and getattr(os, "geteuid", lambda: -1)() == 0:
        options.add_argument("--no-sandbox")
    options.add_argument("--incognito")
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })
    if os.getenv("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
    # Bỏ trống để Selenium Manager tự tìm/tải driver tương thích.
    service = Service(os.getenv("CHROMEDRIVER"))
    browser = webdriver.Chrome(service=service, options=options)
    browser.set_page_load_timeout(45)
    try:
        browser.get(request.config.getoption("--base-url"))
        yield browser
    finally:
        browser.quit()


@pytest.fixture
def store(driver):
    return Store(driver)


@pytest.fixture
def logged_in(store):
    store.login()
    store.wait_for_page("inventory.html")
    return store


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    # Setup lỗi cũng được ghi nhận; chỉ chụp khi còn phiên trình duyệt.
    if report.when != "call" and not report.failed:
        return
    record = {
        "test": item.name,
        "phase": report.when,
        "outcome": report.outcome,
        "duration_seconds": round(report.duration, 3),
    }
    browser = item.funcargs.get("driver")
    if browser is not None:
        try:
            relative = f"screenshots/{item.name}_{report.when}.png"
            if browser.save_screenshot(str(REPORTS / relative)):
                record["screenshot"] = relative
            record["url"] = browser.current_url
            record["browser"] = browser.capabilities.get("browserVersion")
            record["driver"] = browser.capabilities.get("chrome", {}).get("chromedriverVersion")
            extras = getattr(report, "extras", [])
            extras.append(pytest_html.extras.png(browser.get_screenshot_as_base64()))
            report.extras = extras
        except Exception as error:
            record["evidence_error"] = str(error)
    item.config._selenium_results.append(record)


def pytest_sessionfinish(session, exitstatus):
    result = {
        "started_at": session.config._selenium_started,
        "finished_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
        "base_url": session.config.getoption("--base-url"),
        "exit_code": int(exitstatus),
        "results": session.config._selenium_results,
    }
    (REPORTS / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
