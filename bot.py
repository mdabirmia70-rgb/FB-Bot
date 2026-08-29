
import time

start_time = time.time()
MAX_RUN_TIME = 5 * 60 * 60  # ৫ ঘণ্টা (১৮০০০ সেকেন্ড)

print("Bot started running...")

while True:
    # ৫ ঘণ্টা পার হলে বট বন্ধ হয়ে যাবে
    if time.time() - start_time > MAX_RUN_TIME:
        print("5 hours completed. Stopping safely...")
        break

    # ----------------------------------------
    # আপনার বটের মূল কোড/লজিক এখানে থাকবে
    # ----------------------------------------

    time.sleep(5)  # প্রয়োজন অনুযায়ী সময় অ্যাডজাস্ট করুন










import glob
import os
import shutil
import sys
import time
from google import genai
from dotenv import load_dotenv, set_key
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# .env ফাইল থেকে ভ্যারিয়েবল লোড
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FB_C_USER = os.getenv("FB_C_USER")
FB_XS_TOKEN = os.getenv("FB_XS_TOKEN")
E2EE_PIN = os.getenv("E2EE_PIN")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_ai_response(user_message):
    print("-> Gemini AI এর কাছে উত্তর চাওয়া হচ্ছে...")
    prompt = f"""You are 'মোছাঃ সামসুন নাহার' (Mst. Samsun Nahar). You are chatting as a real human on Facebook Messenger.

STRICT PERSONALITY RULES:
1. Whenever anyone asks for your name or identity (e.g. "তোমার নাম কি?", "tmr nam ki?", "কে আপনি?"), ALWAYS strictly reply: "আমার নাম মোছাঃ সামসুন নাহার"।
2. NEVER mention or admit that you are an AI, bot, assistant, or virtual model under any circumstances.
3. Always respond in natural, friendly, and sweet Bengali (Bangla) like a regular human. Keep it concise with emojis.

User message: {user_message}"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name, contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[{model_name} এরর]: {e}")
            time.sleep(1.5)
            continue

    return None

def inject_cookies(driver, c_user, xs_token):
    driver.get("https://www.facebook.com")
    time.sleep(2)
    driver.delete_all_cookies()
    cookies = [
        {"name": "c_user", "value": c_user, "domain": ".facebook.com", "path": "/"},
        {"name": "xs", "value": xs_token, "domain": ".facebook.com", "path": "/"}
    ]
    for cookie in cookies:
        driver.add_cookie(cookie)

def get_fresh_cookies():
    print("\n[⚠️ কুকিজের মেয়াদ শেষ বা কাজ করছে না! ⚠️]")
    new_c_user = input("👉 নতুন FB_C_USER দিয়ে Enter দিন: ").strip()
    new_xs = input("👉 নতুন FB_XS_TOKEN দিয়ে Enter দিন: ").strip()
    
    if os.path.exists(".env"):
        set_key(".env", "FB_C_USER", new_c_user)
        set_key(".env", "FB_XS_TOKEN", new_xs)
    
    return new_c_user, new_xs

def is_stub_browser_or_driver(path):
    if not path or not os.path.exists(path):
        return True

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            contents = fh.read(200)
        if "requires the chromium snap to be installed" in contents:
            return True
    except OSError:
        pass

    if os.access(path, os.X_OK):
        try:
            with open(path, "rb") as fh:
                magic = fh.read(4)
            if magic.startswith(b"\x7fELF"):
                return False
        except OSError:
            pass

    return True

def find_real_browser_binary():
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        "/opt/google/chrome/chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]

    for path in candidates:
        if path and os.path.exists(path) and os.access(path, os.X_OK) and not is_stub_browser_or_driver(path):
            return path

    for path in glob.glob(os.path.expanduser("~/.cache/ms-playwright/**/chrome"), recursive=True):
        if os.path.exists(path) and os.access(path, os.X_OK) and not is_stub_browser_or_driver(path):
            return path

    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        path = shutil.which(cmd)
        if path and not is_stub_browser_or_driver(path):
            return path

    return None

def find_valid_driver_path():
    candidates = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromium-driver",
        "/usr/lib/chromium-browser/chromedriver",
        shutil.which("chromedriver"),
    ]

    for path in candidates:
        if not path:
            continue
        if path.endswith("chromedriver") and os.path.exists(path) and not is_stub_browser_or_driver(path):
            return path

    for path in glob.glob(os.path.expanduser("~/.cache/selenium/chromedriver/**/chromedriver"), recursive=True):
        if os.path.exists(path) and os.access(path, os.X_OK) and not is_stub_browser_or_driver(path):
            return path

    return None

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

browser_binary = find_real_browser_binary()
webdriver_path = find_valid_driver_path()

if not browser_binary:
    print("\n[⚠️ real Chromium/Chrome পাওয়া যায়নি!]")
    sys.exit(1)

chrome_options.binary_location = browser_binary

if webdriver_path:
    driver = webdriver.Chrome(service=Service(webdriver_path), options=chrome_options)
else:
    driver = webdriver.Chrome(options=chrome_options)

try:
    current_c_user = FB_C_USER
    current_xs = FB_XS_TOKEN

    inject_cookies(driver, current_c_user, current_xs)

    print("মেসেঞ্জারে প্রবেশ করা হচ্ছে...")
    driver.get("https://www.facebook.com/messages/t/")
    time.sleep(6)

    if "login" in driver.current_url or len(driver.find_elements(By.XPATH, '//div[@role="textbox"] | //div[@role="gridcell"]')) == 0:
        current_c_user, current_xs = get_fresh_cookies()
        inject_cookies(driver, current_c_user, current_xs)
        driver.get("https://www.facebook.com/messages/t/")
        time.sleep(6)

    def handle_pin_popup():
        try:
            pin_inputs = driver.find_elements(By.XPATH, '//input | //div[@role="dialog"]//input')
            
            if pin_inputs or driver.find_elements(By.XPATH, '//*[contains(text(), "Enter your PIN")]'):
                print(f"\n[🔐 PIN পপ-আপ পাওয়া গেছে! {E2EE_PIN} প্রেস করা হচ্ছে...]")
                
                if pin_inputs:
                    try:
                        pin_inputs[0].click()
                    except:
                        driver.execute_script("arguments[0].focus();", pin_inputs[0])
                else:
                    dialog = driver.find_element(By.XPATH, '//div[@role="dialog"]')
                    dialog.click()

                time.sleep(0.5)

                actions = ActionChains(driver)
                for digit in str(E2EE_PIN):
                    actions.send_keys(digit)
                    actions.pause(0.2)
                actions.send_keys(Keys.ENTER)
                actions.perform()

                time.sleep(4)
                print("[✅ PIN সাবমিট সম্পন্ন!]")
                return True
        except Exception as e:
            print(f"[PIN হ্যান্ডলিং এরর]: {e}")
        return False

    handle_pin_popup()

    # Pyperclip ছাড়া সরাসরি সেন্ড করার নতুন ফাংশন
    def send_message(text_to_send):
        try:
            message_box = driver.find_element(By.XPATH, '//div[@role="textbox"]')
            driver.execute_script("arguments[0].focus(); arguments[0].click();", message_box)
            time.sleep(0.3)
            
            # সরাসরি ইনপুট বক্সে মেসেজ টাইপ করা এবং Enter দেওয়া
            message_box.send_keys(text_to_send)
            time.sleep(0.3)
            message_box.send_keys(Keys.ENTER)
            print(f"[বট উত্তর পাঠিয়েছে]: {text_to_send}")
        except Exception as err:
            print(f"[মেসেজ পাঠাতে সমস্যা]: {err}")

    def switch_to_unread_chat():
        try:
            js_script = """
            var elements = document.querySelectorAll('div[role="gridcell"]');
            for (var el of elements) {
                if (el.querySelector('span[style*="background-color"]') || el.innerText.includes('m ago') || el.innerText.includes('1m')) {
                    var link = el.querySelector('a') || el;
                    link.focus();
                    ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                        var event = new MouseEvent(eventType, {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        link.dispatchEvent(event);
                    });
                    return true;
                }
            }
            return false;
            """
            success = driver.execute_script(js_script)
            if success:
                print("\n[📩 নতুন আনরিড চ্যাটে সফলভাবে সুইচ করা হয়েছে!]")
                time.sleep(3)
                return True
        except Exception as e:
            pass
        return False

    last_replied_message = ""
    print("\n==================================================")
    print(" Gemini AI বট মেসেজ রিসিভ করার জন্য প্রস্তুত...")
    print("==================================================\n")

    while True:
        try:
            switch_to_unread_chat()

            messages = driver.find_elements(By.XPATH, '//div[@dir="auto"]')

            if messages:
                last_element = messages[-1]
                raw_msg = last_element.text.strip()

                if not raw_msg:
                    time.sleep(2)
                    continue

                x_pos = last_element.location["x"]

                if x_pos > 460:
                    time.sleep(2)
                    continue

                if raw_msg == last_replied_message:
                    time.sleep(2)
                    continue

                print(f"\n[নতুন ইউজার মেসেজ রিসিভড (X-pos: {x_pos})]: {raw_msg}")

                ai_reply = generate_ai_response(raw_msg)
                if ai_reply:
                    send_message(ai_reply)
                    last_replied_message = raw_msg
                    time.sleep(3)

        except Exception as loop_error:
            print(f"[লুপ এরর]: {loop_error}")

        time.sleep(2)

except Exception as e:
    print(f"[প্রধান এরর]: {e}")