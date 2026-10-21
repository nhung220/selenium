"""Chrome riêng từng test, tài khoản dữ liệu giả và bằng chứng thực thi."""
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import pytest_html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from pages.hsk import HSK

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / 'reports'
VIETNAM = timezone(timedelta(hours=7))


def pytest_addoption(parser):
    parser.addoption('--headed', action='store_true', help='Hiện cửa sổ Chrome')
    parser.addoption('--base-url', default='https://daln-hsk-app.vercel.app', help='URL website HSK')


def pytest_configure(config):
    (REPORTS / 'screenshots').mkdir(parents=True, exist_ok=True)
    config._selenium_results = []
    config._selenium_started = datetime.now(VIETNAM).isoformat()


def make_browser(config):
    options = webdriver.ChromeOptions()
    if not config.getoption('--headed'):
        options.add_argument('--headless=new')
    options.add_argument('--window-size=1440,1000')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--incognito')
    if getattr(os, 'geteuid', lambda: -1)() == 0:
        options.add_argument('--no-sandbox')
    options.add_experimental_option('prefs', {
        'credentials_enable_service': False,
        'profile.password_manager_enabled': False,
    })
    if os.getenv('CHROME_BINARY'):
        options.binary_location = os.environ['CHROME_BINARY']
    browser = webdriver.Chrome(service=Service(os.getenv('CHROMEDRIVER')), options=options)
    browser.set_page_load_timeout(60)
    return browser


@pytest.fixture(scope='session')
def test_account(request):
    # Có thể dùng tài khoản kiểm thử có sẵn qua biến môi trường.
    email = os.getenv('HSK_TEST_EMAIL')
    password = os.getenv('HSK_TEST_PASSWORD')
    if bool(email) != bool(password):
        pytest.fail('Cần cấu hình đồng thời HSK_TEST_EMAIL và HSK_TEST_PASSWORD.')
    if email and password:
        return {'email': email, 'password': password, 'name': os.getenv('HSK_TEST_NAME', 'Selenium Test')}

    # Một tài khoản giả mỗi lượt chạy, không in hoặc ghi mật khẩu vào báo cáo.
    account = {
        'email': 'selenium.' + uuid.uuid4().hex + '@example.invalid',
        'password': secrets.token_urlsafe(24),
        'name': 'Selenium Test',
    }
    browser = make_browser(request.config)
    app = HSK(browser, request.config.getoption('--base-url'))
    try:
        app.open('/register')
        app.field('Nguyễn Văn A').send_keys(account['name'])
        app.field('ten@email.com').send_keys(account['email'])
        app.field('Ít nhất 6 ký tự').send_keys(account['password'])
        app.submit()
        app.wait.until(lambda d: urlsplit(d.current_url).path != '/register')
        if urlsplit(browser.current_url).path == '/login':
            app.login(account)
        app.user_button(account['name'])
        browser.save_screenshot(str(REPORTS / 'screenshots/setup_test_account.png'))
        return account
    except Exception:
        # Trường hợp lỗi setup chỉ lưu thông tin công khai của tài khoản giả.
        browser.save_screenshot(str(REPORTS / 'screenshots/setup_account_error.png'))
        (REPORTS / 'setup_error.txt').write_text(browser.find_element('tag name', 'body').text, encoding='utf-8')
        raise
    finally:
        browser.quit()


@pytest.fixture
def driver(request):
    browser = make_browser(request.config)
    try:
        yield browser
    finally:
        browser.quit()


@pytest.fixture
def hsk(driver, request):
    return HSK(driver, request.config.getoption('--base-url'))


@pytest.fixture
def logged_in(hsk, test_account):
    hsk.login(test_account)
    return hsk


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != 'call' and not report.failed:
        return
    record = {'test': item.name, 'phase': report.when, 'outcome': report.outcome,
              'duration_seconds': round(report.duration, 3)}
    browser = item.funcargs.get('driver')
    if browser is not None:
        try:
            relative = f'screenshots/{item.name}_{report.when}.png'
            if browser.save_screenshot(str(REPORTS / relative)):
                record['screenshot'] = relative
            url = urlsplit(browser.current_url)
            record['url'] = f'{url.scheme}://{url.netloc}{url.path}'
            record['browser'] = browser.capabilities.get('browserVersion')
            record['driver'] = browser.capabilities.get('chrome', {}).get('chromedriverVersion')
            extras = getattr(report, 'extras', [])
            extras.append(pytest_html.extras.png(browser.get_screenshot_as_base64()))
            report.extras = extras
            if report.failed:
                # DOM công khai để phân tích assertion; không đọc giá trị input/token.
                details = browser.execute_script("""
                  return {text:document.body.innerText,controls:
                    Array.from(document.querySelectorAll('button,input,a'))
                    .filter(e=>e.getClientRects().length)
                    .map(e=>({tag:e.tagName,type:e.getAttribute('type'),
                      placeholder:e.getAttribute('placeholder'),title:e.getAttribute('title'),
                      label:e.getAttribute('aria-label'),text:e.tagName==='INPUT'?'':e.innerText,
                      href:e.tagName==='A'?e.getAttribute('href'):null}))};
                """)
                (REPORTS / f'{item.name}_dom.json').write_text(
                    json.dumps(details, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as error:
            record['evidence_error'] = type(error).__name__
    item.config._selenium_results.append(record)


def pytest_sessionfinish(session, exitstatus):
    if session.config.option.collectonly:
        return
    result = {
        'started_at': session.config._selenium_started,
        'finished_at': datetime.now(VIETNAM).isoformat(),
        'base_url': session.config.getoption('--base-url'),
        'exit_code': int(exitstatus),
        'results': session.config._selenium_results,
    }
    (REPORTS / 'results.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
