"""Page Object cho website thực hành https://www.saucedemo.com/."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class Store:
    def __init__(self, driver, timeout=15):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def element(self, test_id):
        return self.wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, f'[data-test="{test_id}"]')
        ))

    def click(self, test_id):
        self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, f'[data-test="{test_id}"]')
        )).click()

    def fill(self, test_id, value):
        field = self.element(test_id)
        field.clear()
        field.send_keys(value)

    def login(self, username="standard_user", password="secret_sauce"):
        self.fill("username", username)
        self.fill("password", password)
        self.click("login-button")

    def wait_for_page(self, filename):
        self.wait.until(EC.url_contains("/" + filename))

    def add_backpack(self):
        self.click("add-to-cart-sauce-labs-backpack")
        self.wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]'), "1"
        ))

    def open_cart(self):
        self.click("shopping-cart-link")
        self.wait_for_page("cart.html")

    def sort_price_ascending(self):
        Select(self.element("product-sort-container")).select_by_value("lohi")

    def logout(self):
        self.wait.until(EC.element_to_be_clickable(
            (By.ID, "react-burger-menu-btn")
        )).click()
        self.click("logout-sidebar-link")
        self.element("login-button")
