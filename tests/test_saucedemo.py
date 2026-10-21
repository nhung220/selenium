"""Tám test case độc lập; assert kiểm tra kết quả của từng chức năng."""

from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


def test_tc01_login_success(store):
    """TC01: Đăng nhập bằng tài khoản và mật khẩu hợp lệ."""
    store.login()
    store.wait_for_page("inventory.html")
    assert store.element("title").text == "Products"
    assert len(store.driver.find_elements(By.CSS_SELECTOR, '[data-test="inventory-item"]')) == 6


def test_tc02_wrong_password(store):
    """TC02: Từ chối mật khẩu sai, giữ người dùng ở trang đăng nhập."""
    store.login("standard_user", "wrong_password")
    assert store.element("error").text == (
        "Epic sadface: Username and password do not match any user in this service"
    )
    assert store.element("login-button").is_displayed()
    assert "/inventory.html" not in store.driver.current_url


def test_tc03_locked_account(store):
    """TC03: Từ chối tài khoản bị khóa dù mật khẩu đúng."""
    store.login("locked_out_user", "secret_sauce")
    assert store.element("error").text == "Epic sadface: Sorry, this user has been locked out."
    assert store.element("login-button").is_displayed()
    assert "/inventory.html" not in store.driver.current_url


def test_tc04_add_to_cart(logged_in):
    """TC04: Thêm đúng sản phẩm, kiểm tra tên, số lượng và giá trong giỏ."""
    store = logged_in
    store.add_backpack()
    assert store.element("shopping-cart-badge").text == "1"
    store.open_cart()
    assert len(store.driver.find_elements(By.CSS_SELECTOR, '[data-test="inventory-item"]')) == 1
    assert store.element("inventory-item-name").text == "Sauce Labs Backpack"
    assert store.element("item-quantity").text == "1"
    assert store.element("inventory-item-price").text == "$29.99"


def test_tc05_remove_from_cart(logged_in):
    """TC05: Xóa sản phẩm khỏi giỏ; dòng sản phẩm và badge đều biến mất."""
    store = logged_in
    store.add_backpack()
    store.open_cart()
    store.click("remove-sauce-labs-backpack")
    store.wait.until(EC.invisibility_of_element_located(
        (By.CSS_SELECTOR, '[data-test="inventory-item"]')
    ))
    store.wait.until(EC.invisibility_of_element_located(
        (By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]')
    ))
    assert store.driver.find_elements(By.CSS_SELECTOR, '[data-test="inventory-item"]') == []
    assert store.driver.find_elements(By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]') == []


def test_tc06_sort_price_low_to_high(logged_in):
    """TC06: Kiểm tra toàn bộ danh sách giá sau khi chọn Low to High."""
    store = logged_in
    store.sort_price_ascending()

    def sorted_prices(browser):
        prices = [Decimal(e.text.removeprefix("$")) for e in browser.find_elements(
            By.CSS_SELECTOR, '[data-test="inventory-item-price"]'
        )]
        return prices if len(prices) == 6 and prices == sorted(prices) else False

    prices = store.wait.until(sorted_prices)
    assert Select(store.element("product-sort-container")).first_selected_option.get_attribute("value") == "lohi"
    assert prices == sorted(prices)
    assert prices[0] == Decimal("7.99")
    assert prices[-1] == Decimal("49.99")


def test_tc07_checkout_success(logged_in):
    """TC07: Hoàn tất đơn demo và đối chiếu giá tiền trước khi xác nhận."""
    store = logged_in
    store.add_backpack()
    store.open_cart()
    store.click("checkout")
    store.wait_for_page("checkout-step-one.html")
    store.fill("firstName", "Test")
    store.fill("lastName", "Student")
    store.fill("postalCode", "100000")
    store.click("continue")
    store.wait_for_page("checkout-step-two.html")
    assert store.element("inventory-item-name").text == "Sauce Labs Backpack"
    assert store.element("item-quantity").text == "1"
    assert store.element("subtotal-label").text == "Item total: $29.99"
    assert store.element("tax-label").text == "Tax: $2.40"
    assert store.element("total-label").text == "Total: $32.39"
    store.click("finish")
    store.wait_for_page("checkout-complete.html")
    assert store.element("complete-header").text == "Thank you for your order!"
    assert store.driver.find_elements(By.CSS_SELECTOR, '[data-test="shopping-cart-badge"]') == []


def test_tc08_logout(logged_in):
    """TC08: Đăng xuất và kiểm tra URL nội bộ không truy cập được nữa."""
    store = logged_in
    inventory_url = store.driver.current_url
    store.logout()
    assert store.element("login-button").is_displayed()
    assert "/inventory.html" not in store.driver.current_url
    store.driver.get(inventory_url)
    assert store.element("login-button").is_displayed()
    assert store.element("error").text == (
        "Epic sadface: You can only access '/inventory.html' when you are logged in."
    )
    assert "/inventory.html" not in store.driver.current_url
