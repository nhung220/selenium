"""Khảo sát DOM bằng Selenium với dữ liệu giả; không in mật khẩu/cookie."""
import json
import secrets
import uuid
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

BASE = "https://daln-hsk-app.vercel.app"
Path("reports").mkdir(exist_ok=True)
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1000")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(60)
wait = WebDriverWait(driver, 45)


def snapshot(name):
    # Chỉ đọc các phần tử DOM, không đọc state nội bộ, token hay giá trị input.
    state = driver.execute_script("""
      return {
        path: location.pathname,
        text: document.body.innerText.slice(0,11000),
        controls: Array.from(document.querySelectorAll('input,select,button,a'))
          .filter(e => e.getClientRects().length)
          .map(e => ({tag:e.tagName,type:e.getAttribute('type'),
            id:e.id,placeholder:e.getAttribute('placeholder'),
            label:e.getAttribute('aria-label'),title:e.getAttribute('title'),
            text:e.tagName==='INPUT'?'':e.innerText.slice(0,100),
            href:e.tagName==='A'?e.getAttribute('href'):null}))
      };
    """)
    print("PAGE " + name + " " + json.dumps(state, ensure_ascii=False), flush=True)
    Path(f"reports/inspect_{name}.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    driver.save_screenshot(f"reports/inspect_{name}.png")


try:
    email = "selenium." + uuid.uuid4().hex + "@example.invalid"
    password = secrets.token_urlsafe(24)
    driver.get(BASE + "/register")
    wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, 'input[type="email"]'))
    driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Nguyễn Văn A"]').send_keys("Selenium Test")
    driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys(email)
    driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    wait.until(lambda d: "/register" not in d.current_url)
    if "/login" in driver.current_url:
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, 'input[type="email"]'))
        driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys(email)
        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        wait.until(lambda d: "/login" not in d.current_url)
    snapshot("registration_result")
    if "/register" in driver.current_url or "/login" in driver.current_url:
        raise RuntimeError("Chưa xác nhận đăng ký và đăng nhập thành công; xem DOM thực tế.")
    for path in ["/vocabulary", "/search", "/review", "/grammar", "/notebook", "/progress"]:
        driver.get(BASE + path)
        wait.until(lambda d: len(d.find_element(By.TAG_NAME, 'body').text)>150)
        # Chờ dữ liệu bất đồng bộ hiển thị, không giả lập dữ liệu trang.
        wait.until(lambda d: not any(e.is_displayed() for e in d.find_elements(
            By.XPATH, "//*[self::p or self::div or self::span][normalize-space(.)='Đang tải...']")))
        snapshot(path.strip("/"))
except Exception:
    snapshot("failure")
    raise
finally:
    driver.quit()
