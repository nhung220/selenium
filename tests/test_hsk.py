"""10 test case độc lập trên website HSK, gồm dữ liệu đúng và sai."""
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By


def test_tc01_login_required_fields(hsk):
    """Bỏ trống email/mật khẩu: form chặn gửi bằng HTML5 validation."""
    hsk.open('/login')
    email = hsk.field('ten@email.com')
    password = hsk.field('Ít nhất 6 ký tự')
    hsk.submit()
    assert hsk.driver.execute_script('return arguments[0].validity.valueMissing', email)
    assert hsk.driver.execute_script('return arguments[0].validity.valueMissing', password)
    assert hsk.driver.switch_to.active_element == email
    assert urlsplit(hsk.driver.current_url).path == '/login'


def test_tc02_invalid_email_format(hsk):
    """Email sai định dạng bị chặn ở trình duyệt trước khi xác thực server."""
    hsk.open('/login')
    email = hsk.field('ten@email.com')
    email.send_keys('email-khong-hop-le')
    hsk.field('Ít nhất 6 ký tự').send_keys('SyntheticPassword123!')
    hsk.submit()
    assert hsk.driver.execute_script('return arguments[0].validity.typeMismatch', email)
    assert hsk.driver.switch_to.active_element == email
    assert urlsplit(hsk.driver.current_url).path == '/login'


def test_tc03_toggle_password_visibility(hsk):
    """Nút hiện/ẩn đổi loại input, giữ nguyên chuỗi mật khẩu giả."""
    hsk.open('/login')
    password = hsk.field('Ít nhất 6 ký tự')
    password.send_keys('SyntheticPassword123!')
    assert password.get_attribute('type') == 'password'
    toggle = hsk.driver.find_element(By.CSS_SELECTOR, 'form button[type="button"]')
    toggle.click()
    assert password.get_attribute('type') == 'text'
    assert password.get_attribute('value') == 'SyntheticPassword123!'
    toggle.click()
    assert password.get_attribute('type') == 'password'
    assert password.get_attribute('value') == 'SyntheticPassword123!'


def test_tc04_protected_search_requires_login(hsk):
    """Khách chưa đăng nhập không được dùng tra từ."""
    hsk.open('/search')
    email = hsk.field('ten@email.com')
    assert urlsplit(hsk.driver.current_url).path == '/login'
    assert email.is_displayed()
    assert hsk.driver.find_elements(By.CSS_SELECTOR,
        'input[placeholder="Ví dụ: 你好, nihao, xin chào..."]') == []


def test_tc05_login_success(logged_in, test_account):
    """Đăng nhập hợp lệ phải vào từ vựng và hiển thị đúng người dùng."""
    hsk = logged_in
    assert urlsplit(hsk.driver.current_url).path == '/vocabulary'
    assert hsk.user_button(test_account['name']).is_displayed()
    assert hsk.text('Từ Vựng HSK 3.0').is_displayed()
    assert hsk.driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]') == []


def test_tc06_select_hsk1(logged_in):
    """Chọn cấp HSK 1 phải hiển thị danh sách bài học tương ứng."""
    hsk = logged_in
    hsk.button('Bắt đầu từ HSK 1').click()
    hsk.wait.until(lambda d: 'Bài 1' in d.find_element(By.TAG_NAME, 'body').text)
    body = hsk.driver.find_element(By.TAG_NAME, 'body').text
    assert 'HSK 1' in body
    assert 'Bài 1' in body
    assert len(hsk.driver.find_elements(By.XPATH,
        '//*[self::a or self::button][contains(., "Bài 1")]')) > 0


def test_tc07_search_existing_word(logged_in):
    """Tra chữ Hán phải trả về đúng chữ và pinyin của từ."""
    hsk = logged_in
    hsk.search('你好')
    assert hsk.text('你好').is_displayed()
    assert hsk.text('nǐ hǎo').is_displayed()
    assert urlsplit(hsk.driver.current_url).path == '/search'


def test_tc08_search_no_results(logged_in):
    """Chuỗi không có trong từ điển phải có trạng thái không tìm thấy."""
    hsk = logged_in
    hsk.search('zzzz_selenium_no_match_2026')
    expected = ('Không tìm thấy', 'Không có kết quả', '0 kết quả')
    body = hsk.wait.until(lambda d: (
        d.find_element(By.TAG_NAME, 'body').text
        if any(s in d.find_element(By.TAG_NAME, 'body').text for s in expected) else False))
    assert any(s in body for s in expected)
    assert hsk.field('Ví dụ: 你好, nihao, xin chào...').get_attribute('value') == 'zzzz_selenium_no_match_2026'
    assert urlsplit(hsk.driver.current_url).path == '/search'


def test_tc09_review_empty_state(logged_in):
    """Tài khoản mới chưa học từ phải có trạng thái ôn tập trống."""
    hsk = logged_in
    hsk.open('/review')
    assert hsk.text('Xong rồi!').is_displayed()
    hsk.wait.until(lambda d: 'Không có từ nào cần ôn hôm nay' in d.find_element(By.TAG_NAME, 'body').text)
    assert hsk.driver.find_element(By.LINK_TEXT, 'Học bài mới').get_attribute('href') == hsk.base_url + '/vocabulary'


def test_tc10_logout_protects_session(logged_in, test_account):
    """Đăng xuất xong phải chặn lại tra từ dù mở URL trực tiếp."""
    hsk = logged_in
    hsk.logout(test_account['name'])
    hsk.open('/search')
    assert hsk.field('ten@email.com').is_displayed()
    assert urlsplit(hsk.driver.current_url).path == '/login'
    assert hsk.driver.find_elements(By.XPATH,
        '//nav//button[contains(., "Selenium Test")]') == []
