import telegram_module as tg
import glob
import os
import shutil
import sys
import time
import random
import requests
from datetime import datetime, timezone, timedelta
from google import genai
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# config.py ফাইল থেকে ইমপোর্ট
from config import MODELS_TO_TRY, SYSTEM_INSTRUCTION

# .env ফাইল থেকে ভ্যারিয়েবল লোড
load_dotenv()

raw_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY")
]
API_KEYS = [k for k in raw_keys if k]
current_key_index = 0

FB_C_USER = os.getenv("FB_C_USER")
FB_XS_TOKEN = os.getenv("FB_XS_TOKEN")
E2EE_PIN = os.getenv("E2EE_PIN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

chat_sessions = {}

def get_current_time_context():
    bd_tz = timezone(timedelta(hours=6))
    now = datetime.now(bd_tz)
    return f"(Current Time: {now.strftime('%I:%M %p')})"

def fetch_screen_history():
    try:
        messages = driver.find_elements(By.XPATH, '//div[@role="row"]//div[@dir="auto"] | //div[@dir="auto"]')
        if len(messages) > 1:
            history_elements = messages[-20:-1]
            recent_history_list = []
            for el in history_elements:
                txt = el.text.strip()
                if txt:
                    sender = "বট (সামসুন Nahar)" if el.location["x"] > 550 else "ইউজার"
                    recent_history_list.append(f"{sender}: {txt}")
            return "\n".join(recent_history_list)
    except Exception as e:
        print(f"[হিস্ট্রি রিড এরর]: {e}")
    return ""

def generate_ai_response(user_message, chat_id="default_chat", attempt_count=1):
    global current_key_index
    print(f"-> Gemini AI এর কাছে উত্তর চাওয়া হচ্ছে (চ্যাট ID: {chat_id[-10:]}, Attempt: {attempt_count})...")

    time_info = get_current_time_context()
    recent_history = fetch_screen_history()

    if API_KEYS:
        for _ in range(len(API_KEYS)):
            current_api_key = API_KEYS[current_key_index]
            key_number = current_key_index + 1
            
            for model_name in MODELS_TO_TRY:
                try:
                    client = genai.Client(api_key=current_api_key)
                    prompt_with_context = f"চ্যাটের আগের ব্যাকগ্রাউন্ড হিস্ট্রি:\n{recent_history}\n\nইউজারের নতুন মেসেজ: {user_message} {time_info}"
                    
                    chat_obj = client.chats.create(
                        model=model_name,
                        config={"system_instruction": SYSTEM_INSTRUCTION}
                    )
                    response = chat_obj.send_message(prompt_with_context)
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    err_str = str(e)
                    
                    if "404" in err_str or "NOT_FOUND" in err_str:
                        print(f"[API Key {key_number}]: {model_name} মডেলটি পাওয়া যায়নি।")
                        continue
                        
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                        error_log = f"⚠️ *[API Key {key_number}]-এর কোটা/লিমিট শেষ!* (Model: `{model_name}`)"
                        print(error_log)
                        tg.send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, error_log)
                        break

            current_key_index = (current_key_index + 1) % len(API_KEYS)

    alert_all = "🚨 *সবগুলো Gemini API Key-এর লিমিট শেষ!* দয়া করে ম্যানুয়াল উত্তর পাঠাতে পারেন।"
    print(f"[{alert_all}]")
    
    telegram_reply = tg.get_telegram_reply(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, user_message)
    if telegram_reply:
        return telegram_reply
    else:
        time.sleep(2)
        return generate_ai_response(user_message, chat_id=chat_id, attempt_count=attempt_count+1)

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
    return False

def find_real_browser_binary():
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for path in candidates:
        if os.path.exists(path) and os.access(path, os.X_OK) and not is_stub_browser_or_driver(path):
            return path
    return shutil.which("google-chrome") or shutil.which("google-chrome-stable")

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

browser_binary = find_real_browser_binary()
if browser_binary:
    chrome_options.binary_location = browser_binary

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    inject_cookies(driver, FB_C_USER, FB_XS_TOKEN)
    print("মেসেঞ্জারে প্রবেশ করা হচ্ছে...")
    driver.get("https://www.facebook.com/messages/t/")
    time.sleep(6)

    if "login" in driver.current_url or len(driver.find_elements(By.XPATH, '//div[@role="textbox"] | //div[@role="gridcell"]')) == 0:
        alert_msg = "⚠️ [FB Bot Alert] কুকিজের মেয়াদ শেষ বা লগইন ব্যর্থ হয়েছে!\nদয়া করে GitHub Secrets-এ নতুন কুকিজ আপডেট করে Workflow পুনরায় রান দিন।"
        print(f"\n[{alert_msg}]")
        tg.send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, alert_msg)
        sys.exit(1)

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

    def send_message(text_to_send):
        try:
            MAX_CHUNK_LIMIT = 145
            message_chunks = []

            lines = [line.strip() for line in text_to_send.split("\n") if line.strip()]
            current_chunk = ""

            for line in lines:
                if len(current_chunk) + len(line) + 1 <= MAX_CHUNK_LIMIT:
                    current_chunk = f"{current_chunk} {line}".strip()
                else:
                    if current_chunk:
                        message_chunks.append(current_chunk)
                    while len(line) > MAX_CHUNK_LIMIT:
                        split_pos = line.rfind(" ", 0, MAX_CHUNK_LIMIT)
                        if split_pos == -1:
                            split_pos = MAX_CHUNK_LIMIT
                        message_chunks.append(line[:split_pos].strip())
                        line = line[split_pos:].strip()
                    current_chunk = line

            if current_chunk:
                message_chunks.append(current_chunk)

            for chunk_index, chunk in enumerate(message_chunks):
                msg_length = len(chunk)
                char_delay_min, char_delay_max = 0.20, 0.28

                if chunk_index == 0:
                    time.sleep(random.uniform(1.0, 2.0))
                else:
                    time.sleep(random.uniform(3.0, 4.0))

                message_box = driver.find_element(By.XPATH, '//div[@role="textbox"]')
                message_box.click()
                time.sleep(0.3)
                print(f"-> টাইপিং পার্ট {chunk_index + 1}/{len(message_chunks)} ({msg_length} টি অক্ষর)...")

                for char in chunk:
                    actions = ActionChains(driver)
                    actions.send_keys(char)
                    actions.perform()
                    time.sleep(random.uniform(char_delay_min, char_delay_max))

                time.sleep(random.uniform(0.6, 1.2))
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                print(f"[বট অংশটি পাঠিয়েছে]: {chunk}")

        except Exception as err:
            print(f"[মেসেজ পাঠাতে সমস্যা]: {err}")

    def get_chat_unique_id():
        try:
            url = driver.current_url
            if "/t/" in url:
                chat_id = url.split("/t/")[-1].replace("/", "")
                if chat_id:
                    return chat_id
        except:
            pass
        return "default_chat"

    def switch_to_unread_chat():
        try:
            chats = driver.find_elements(By.XPATH, '//div[@role="gridcell"]')
            for chat in chats:
                if chat.find_elements(By.XPATH, './/span[contains(@style, "background-color")]') or "m ago" in chat.text or "1m" in chat.text:
                    chat.click()
                    print("\n[📩 নতুন আনরিড চ্যাটে সফলভাবে সুইচ করা হয়েছে!]")
                    time.sleep(3)
                    return True
        except Exception as e:
            pass
        return False

    last_replied_message = ""
    start_time = time.time()
    MAX_RUN_TIME = 5 * 60 * 60

    print("\n==================================================")
    print(" Gemini AI বট মেসেজ রিসিভ করার জন্য প্রস্তুত...")
    print("==================================================\n")

    tg.send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "🚀 *FB Auto-Reply Bot সফলভাবে চালু হয়েছে!*")
    tg.send_telegram_menu(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

    while True:
        if time.time() - start_time > MAX_RUN_TIME:
            print("5 hours completed. Stopping safely...")
            break

        # টেলিগ্রাম থেকে ইনপুট/কমান্ড চেক
        tg.check_telegram_commands(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

        # বট অফলাইন থাকলে কোনো চ্যাটের মধ্যে থাকবে না এবং মেসেঞ্জারের প্রধান হোমে চলে যাবে
        if tg.is_bot_paused:
            if "/messages/t/" in driver.current_url:
                try:
                    driver.get("https://www.facebook.com")
                    print("[🔒 বট অফলাইন: চ্যাট উইন্ডো বন্ধ করা হয়েছে যাতে মেসেজ Seen না হয়]")
                except Exception as e:
                    pass
            time.sleep(3)
            continue

        try:
            # বট অনলাইন হলে পুনরায় মেসেঞ্জার পেজে ব্যাক করবে
            if "/messages/t/" not in driver.current_url:
                driver.get("https://www.facebook.com/messages/t/")
                time.sleep(5)

            # নতুন আনরিড চ্যাটে ঢুকবে
            switch_to_unread_chat()
            current_chat_id = get_chat_unique_id()

            messages = driver.find_elements(By.XPATH, '//div[@role="row"]//div[@dir="auto"] | //div[@dir="auto"]')
            if messages:
                last_element = messages[-1]
                raw_msg = last_element.text.strip()

                if not raw_msg:
                    time.sleep(2)
                    continue

                x_pos = last_element.location["x"]
                if x_pos > 550:
                    time.sleep(2)
                    continue

                if raw_msg == last_replied_message:
                    time.sleep(2)
                    continue

                print(f"\n[নতুন মেসেজ রিসিভড (ID: {current_chat_id})]: {raw_msg}")
                ai_reply = generate_ai_response(raw_msg, chat_id=current_chat_id)

                if ai_reply:
                    send_message(ai_reply)
                    last_replied_message = raw_msg
                    time.sleep(2)
                else:
                    print("[⚠️ উত্তর পাওয়া যায়নি!]")

        except Exception as loop_error:
            print(f"[লুপ এরর]: {loop_error}")
            time.sleep(2)






except Exception as e:
    err_msg = f"⚠️ [FB Bot Error]: {e}"
    print(f"[{err_msg}]")
    tg.send_telegram_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, err_msg)
finally:
    try:
        driver.quit()
    except:
        pass
