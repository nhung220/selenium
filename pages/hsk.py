"""Page Object theo các phần tử thực tế của daln-hsk-app.vercel.app."""
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class HSK:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url.rstrip('/')
        self.wait = WebDriverWait(driver, 40)

    def open(self, path):
        self.driver.get(self.base_url + path)

    def field(self, placeholder):
        return self.wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, f'input[placeholder="{placeholder}"]')))

    def submit(self):
        self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[type="submit"]'))).click()

    def text(self, text):
        # Chuỗi truyền vào ở đây là hằng số test, không chứa dữ liệu tài khoản.
        return self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, f'//*[normalize-space(.)="{text}"]')))

    def button(self, text):
        return self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f'//button[normalize-space(.)="{text}"]')))

    def user_button(self, name='Selenium Test'):
        return self.wait.until(EC.visibility_of_element_located(
            (By.XPATH, f'//nav//button[contains(., "{name}")]')))

    def login(self, account):
        self.open('/login')
        self.field('ten@email.com').send_keys(account['email'])
        self.field('Ít nhất 6 ký tự').send_keys(account['password'])
        self.submit()
        self.wait.until(lambda d: urlsplit(d.current_url).path == '/vocabulary')
        self.user_button(account['name'])

    def search(self, query):
        self.open('/search')
        field = self.field('Ví dụ: 你好, nihao, xin chào...')
        field.clear()
        field.send_keys(query)

    def logout(self, name):
        self.user_button(name).click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH,
            '//*[self::button or self::a][normalize-space(.)="Đăng xuất"]'))).click()
        self.wait.until(lambda d: urlsplit(d.current_url).path in ['/', '/login'])
