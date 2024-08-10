import os
import requests
import logging
import time
import pickle
import winsound
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client

# Setup logging to debug the process with timestamps
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Twilio credentials
TWILIO_ACCOUNT_SID = 'ENTER_YOUR_TWILIO_ACCOUNT_SID'
TWILIO_AUTH_TOKEN = 'ENTER_YOUR_TWILIO_AUTH_TOKEN'
TWILIO_PHONE_NUMBER = 'ENTER_YOUR_TWILIO_PHONE_NUMBER'
TO_PHONE_NUMBER = 'ENTER_THE_PHONE_NUMBER_TO_NOTIFY'

# 2Captcha API key for solving CAPTCHA
TWO_CAPTCHA_API_KEY = 'ENTER_YOUR_2CAPTCHA_API_KEY'

# Path to store cookies for session management
COOKIES_FILE = 'cookies/cookies.pkl'

# Login credentials for the website
USERNAME = "ENTER_YOUR_USERNAME"
PASSWORD = "ENTER_YOUR_PASSWORD"

def initialize_driver():
    """Initialize the WebDriver with custom settings for Edge."""
    logging.info('Initializing WebDriver...')
    try:
        # Path to the Edge WebDriver
        edge_driver_path = 'C:/Users/usama/OneDrive/Desktop/WebDrivers/edgedriver_win64/msedgedriver.exe'
        service = Service(executable_path=edge_driver_path)
        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")  # Start browser maximized
        options.add_argument("--disable-blink-features=AutomationControlled")  # Reduce bot detection
        options.add_experimental_option('excludeSwitches', ['enable-automation'])  # Hide automation info
        options.add_experimental_option('useAutomationExtension', False)  # Disable automation extension
        driver = webdriver.Edge(service=service, options=options)
        driver.implicitly_wait(10)  # Implicit wait for elements
        logging.info('WebDriver initialized successfully.')
        return driver
    except Exception as e:
        logging.error(f'Failed to initialize WebDriver: {e}')
        return None

def wait_for_element(driver, by, value, timeout=30):
    """Wait for a specific element to appear on the page."""
    logging.info(f'Waiting for element: {value}')
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return element
    except Exception as e:
        logging.error(f'Error waiting for element {value}: {e}')
        return None

def handle_popups(driver):
    """Close any popups that might appear on the page."""
    logging.info('Handling popups...')
    try:
        popup_close_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.pop-close'))
        )
        popup_close_button.click()
        logging.info('Popup closed.')
    except Exception as e:
        logging.debug(f'No popup found or couldn\'t close popup: {e}')

def save_cookies(driver):
    """Save session cookies to a file."""
    logging.info('Saving cookies...')
    try:
        os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
        with open(COOKIES_FILE, 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        logging.info('Cookies saved successfully.')
    except Exception as e:
        logging.error(f'Error saving cookies: {e}')

def load_cookies(driver):
    """Load session cookies from a file if it exists."""
    if os.path.exists(COOKIES_FILE):
        logging.info('Loading cookies...')
        try:
            driver.get('https://blsitalypakistan.com/')
            with open(COOKIES_FILE, 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            logging.info('Cookies loaded successfully.')
        except Exception as e:
            logging.error(f'Error loading cookies: {e}')
    else:
        logging.info('No cookies file found, proceeding to login.')

def fill_login_form(driver, username, password):
    """Fill in the login form with provided credentials."""
    logging.info('Filling login form...')
    try:
        # Enter the username
        username_field = wait_for_element(driver, By.XPATH, '//input[@type="text" and @class="form-control"]')
        if username_field:
            username_field.clear()
            username_field.send_keys(username)
        else:
            logging.error('Username field not found.')

        # Enter the password
        password_field = wait_for_element(driver, By.XPATH, '//input[@type="password" and @name="login_password" and @class="form-control"]')
        if password_field:
            password_field.clear()
            password_field.send_keys(password)
        else:
            logging.error('Password field not found.')
    except Exception as e:
        logging.error(f'Error filling the login form: {e}')

def solve_captcha(driver):
    """Solve CAPTCHA using the 2Captcha service."""
    logging.info('Solving CAPTCHA...')
    try:
        # Locate the CAPTCHA image
        captcha_image = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img[src*="captcha"]'))
        )
        captcha_image.screenshot('captcha.png')  # Save CAPTCHA image locally

        # Send CAPTCHA image to 2Captcha for solving
        with open('captcha.png', 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'https://2captcha.com/in.php?key={TWO_CAPTCHA_API_KEY}&method=post',
                files=files
            )
        
        if response.text.startswith('OK'):
            captcha_id = response.text.split('|')[1]
            logging.info(f'CAPTCHA ID received: {captcha_id}')
        else:
            logging.error(f'2Captcha error: {response.text}')
            return None
        
        # Poll 2Captcha for the solution
        for _ in range(20):
            time.sleep(5)
            result_response = requests.get(
                f'https://2captcha.com/res.php?key={TWO_CAPTCHA_API_KEY}&action=get&id={captcha_id}'
            )
            if result_response.text == 'CAPCHA_NOT_READY':
                logging.info('CAPTCHA not ready, waiting...')
                continue
            elif result_response.text.startswith('OK'):
                captcha_text = result_response.text.split('|')[1]
                logging.info(f'CAPTCHA text received: {captcha_text}')
                return captcha_text
            else:
                logging.error(f'2Captcha error: {result_response.text}')
                return None
        
        logging.error('CAPTCHA solving failed after multiple attempts.')
        return None
    except Exception as e:
        logging.error(f'Error solving the CAPTCHA: {e}')
        return None

def click_element(driver, by, value, retries=3):
    """Click an element on the page, retrying if necessary."""
    for i in range(retries):
        try:
            element = wait_for_element(driver, by, value)
            if element:
                driver.execute_script("arguments[0].scrollIntoView();", element)  # Scroll to element
                element.click()
                logging.info(f'Clicked element: {value}')
                return
        except Exception as e:
            logging.warning(f'Retry {i+1}: Element not clickable, retrying... {e}')
            time.sleep(1)
    logging.error(f'Failed to click element: {value}')

def login(driver, username, password):
    """Log in to the website and navigate to the desired page."""
    driver.get('https://blsitalypakistan.com/')
    load_cookies(driver)

    logging.info('Reloading the page twice for stability...')
    driver.refresh()
    time.sleep(2)
    driver.refresh()

    handle_popups(driver)

    max_retries = 3
    for attempt in range(max_retries):
        logging.info(f'Login attempt {attempt+1}/{max_retries}...')
        try:
            # Click the LOGIN link
            click_element(driver, By.LINK_TEXT, 'LOGIN')
            
            # Fill in login credentials and solve CAPTCHA
            fill_login_form(driver, username, password)
            captcha_text = solve_captcha(driver)
            if captcha_text:
                captcha_input = wait_for_element(driver, By.ID, 'captcha_code_reg')
                if captcha_input:
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    click_element(driver, By.NAME, 'submitLogin')

                    # Check if login was successful
                    if WebDriverWait(driver, 10).until(EC.url_contains('/account/account_details')):
                        logging.info('Successfully logged in and redirected to the dashboard.')
                        save_cookies(driver)
                        return True
                    else:
                        logging.warning('Incorrect CAPTCHA code, retrying...')
                        driver.get('https://blsitalypakistan.com/account/login')
                else:
                    logging.error('CAPTCHA input field not found.')
            else:
                logging.error('Failed to solve CAPTCHA, retrying...')

        except Exception as e:
            logging.error(f'Login attempt failed: {e}')
            driver.get('https://blsitalypakistan.com/account/login')
    
    logging.error('All login attempts failed.')
    return False

def monitor_appointment_date(driver, target_date):
    """Monitor the appointment date section and notify if the target date is available."""
    logging.info(f'Monitoring for target appointment date: {target_date}...')
    try:
        while True:
            # Navigate to the appointment page
            driver.get('https://blsitalypakistan.com/account/account_details')
            appointment_date_element = wait_for_element(driver, By.CSS_SELECTOR, 'h4.time-title')

            if appointment_date_element:
                appointment_date = appointment_date_element.text.strip()
                logging.info(f'Current appointment date: {appointment_date}')
                
                if appointment_date == target_date:
                    logging.info('Target appointment date is available! Sending notification...')
                    # Send SMS notification via Twilio
                    send_sms_notification(appointment_date)
                    
                    # Play a sound notification
                    winsound.Beep(1000, 1000)  # Frequency: 1000 Hz, Duration: 1000 ms
                    return True
                else:
                    logging.info(f'Target date not available. Retrying in 60 seconds...')
                    time.sleep(60)
            else:
                logging.error('Appointment date element not found.')
                time.sleep(60)
    except Exception as e:
        logging.error(f'Error monitoring the appointment date: {e}')

def send_sms_notification(appointment_date):
    """Send an SMS notification using Twilio."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f'Target appointment date {appointment_date} is now available!',
            from_=TWILIO_PHONE_NUMBER,
            to=TO_PHONE_NUMBER
        )
        logging.info(f'SMS notification sent successfully: SID {message.sid}')
    except Exception as e:
        logging.error(f'Failed to send SMS notification: {e}')

if __name__ == "__main__":
    driver = initialize_driver()
    if driver:
        try:
            if login(driver, USERNAME, PASSWORD):
                # Monitor a specific appointment date
                target_appointment_date = '30/09/2024'
                monitor_appointment_date(driver, target_appointment_date)
        finally:
            driver.quit()
            logging.info('WebDriver session ended.')
