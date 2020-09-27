import sys
import time
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# Log in to Steam with the user's username and password
def log_in(driver, username, password):
    username_element = driver.find_element_by_id('steamAccountName')
    username_element.click()
    username_element.clear()
    username_element.send_keys(username)

    password_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'steamPassword')))
    password_element.click()
    password_element.clear()
    password_element.send_keys(password)

    driver.find_element_by_id('SteamLogin').click()

    # Handle login errors including too many log-ins and wrong credentials
    time.sleep(5)
    if driver.find_element_by_id('error_display').is_displayed():
        error_text = driver.find_element_by_id('error_display').text
        print(error_text)
        # If the error is "too many logins" error then close the application
        if "too many login failures" in error_text:
            sys.exit("Stopping application. Try again later")
        else:
            # While the login credentials are incorrect, keep asking the user for the correct credentials
            while driver.find_element_by_id('error_display').is_displayed():
                print("Please give your Steam username and password again.\n")
                return False
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'error_display')))
    else:
        return True


# After logging in, ask the user for the security code from their email
def enter_email_code(driver, email_code):
    # wait for the email code pop-up to appear before entering it
    WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='auth_buttonset_entercode']/div[1]")))
    email_element = driver.find_element_by_id('authcode')
    email_element.send_keys(email_code)

    # Submit the security code and continue
    driver.find_element_by_xpath("//div[@id='auth_buttonset_entercode']/div[1]").click()
    try:
        driver.find_element_by_class_name("newmodal_close").click()
    except ElementNotInteractableException:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "success_continue_btn"))).click()

    # If the provided email code is incorrect then ask again
    if driver.current_url == "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F":
        print("\nSecurity code is incorrect. Please try again.\n")
        time.sleep(3)
        return False
