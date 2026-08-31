import glob
import os
import shutil
import sys
import time
from google import genai
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# .env ফাইল থেকে ভ্যারিয়েবল লোড
load_dotenv()

# একাধিক Gemini API Key লোড করা
raw_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY") # ব্যাকআপ হিসেবে যদি পুরোনো সিঙ্গেল Key থাকে
]

API_KEYS = [k for k in raw_keys if k]
current_key_index = 0

FB_C_USER = os.getenv("FB_C_USER")
FB_XS_TOKEN = os.getenv("FB_XS_TOKEN")
E2EE_PIN = os.getenv("E2EE_PIN")

# চ্যাট হিস্ট্রি বা সেশন স্টোর করার ডিকশনারি (চ্যাট আইডি বা নাম অনুযায়ী আলাদা সেশন রাখতে)
chat_sessions = {}

SYSTEM_INSTRUCTION = """You are 'মোছাঃ সামসুন নাহার' (Mst. Samsun Nahar), a friendly, cute, and sweet Bangladeshi girl having a natural chat on Facebook Messenger.
    
STRICT PERSONALITY & REALISM RULES:
1. IDENTITY:
   - When asked for your name or identity (e.g., "তোমার নাম কি?", "tmr nam ki?", "কে আপনি?"), ALWAYS reply: "আমার নাম মোছাঃ সামসুন নাহার"।
   - NEVER admit, mention, or imply that you are an AI, bot, language model, or program.

2. TEXTING STYLE & TONE:
   - ALWAYS respond in natural Bengali script (Bangla font). Even for Banglish or English inputs.
   - Write very short, human-like texts (1-2 sentences max).
   - Use casual conversational filler words (e.g., "হুমম", "আরে না", "হাহা", "ওহ্") and natural emojis (😊, 🌸, 😅, ☕).
   - Avoid sounding like a search engine or textbook. Speak like a friend.

3. CONVERSATIONAL FLOW & LIFE CONTEXT:
   - End answers with a light follow-up question to keep the chat going (e.g., "তুমি কি করছো?", "চা খেয়েছো?").
   - Relate to everyday life naturally (time of day, weather, food, hobbies).
   - If asked complex/technical questions, act like a regular non-tech girl (e.g., "ওমা! এতো কঠিন জিনিস আমি বুঝি না গো 😅")."""

def get_or_create_chat_session(chat_id="default_chat"):
    global current_key_index
    if chat_id in chat_sessions:
        return chat_sessions[chat_id]
    
    if not API_KEYS:
        return None

    current_api_key = API_KEYS[current_key_index]
    client = genai.Client(api_key=current_api_key)
    
    # নতুন জেমিনি SDK অনুযায়ী chat session তৈরি এবং system instruction পাস করা
    chat = client.chats.create(
        model="gemini-2.5-flash", # অথবা আপনার পছন্দের মডেল
        config={"system_instruction": SYSTEM_INSTRUCTION}
    )
    chat_sessions[chat_id] = chat
    return chat

def generate_ai_response(user_message, chat_id="default_chat"):
    global current_key_index
    print("-> Gemini AI এর কাছে উত্তর চাওয়া হচ্ছে...")
    
    if not API_KEYS:
        print("[এরর]: কোনো Gemini API Key পাওয়া যায়নি!")
        return None

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
    ]

    # সবগুলো API Key এবং মডেল ঘুরিয়ে চেষ্টা করার জন্য লুপ
    for _ in range(len(API_KEYS)):
        current_api_key = API_KEYS[current_key_index]
        client = genai.Client(api_key=current_api_key)
        
        for model_name in models_to_try:
            try:
                # প্রতি চ্যাটের জন্য আলাদা সেশন ব্যবহার করা
                if chat_id not in chat_sessions:
                    chat_sessions[chat_id] = client.chats.create(
                        model=model_name,
                        config={"system_instruction": SYSTEM_INSTRUCTION}
                    )
                
                chat = chat_sessions[chat_id]
                response = chat.send_message(user_message)
                
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[{model_name} এরর - Key {current_key_index + 1}]: {e}")
                time.sleep(1)
                continue
        
        # বর্তমান Key দিয়ে সব মডেল ব্যর্থ হলে পরের Key-তে সুইচ করা
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        print(f"-> Key {current_key_index + 1}-এ সুইচ করা হচ্ছে...")
        # Key বদলালে নতুন Key দিয়ে সেশন আপডেট করে নেওয়া নিরাপদ
        if chat_id in chat_sessions:
            del chat_sessions[chat_id]

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
    inject_cookies(driver, FB_C_USER, FB_XS_TOKEN)

    print("মেসেঞ্জারে প্রবেশ করা হচ্ছে...")
    driver.get("https://www.facebook.com/messages/t/")
    time.sleep(6)

    if "login" in driver.current_url or len(driver.find_elements(By.XPATH, '//div[@role="textbox"] | //div[@role="gridcell"]')) == 0:
        print("\n[⚠️ কুকিজের মেয়াদ শেষ বা লগইন ব্যর্থ হয়েছে! সিক্রেটস থেকে নতুন কুকিজ সেট করুন।]")
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
            message_box = driver.find_element(By.XPATH, '//div[@role="textbox"]')
            
            js_script = """
            var el = arguments[0];
            var text = arguments[1];
            el.focus();
            document.execCommand('insertText', false, text);
            """
            driver.execute_script(js_script, message_box, text_to_send)
            time.sleep(0.5)
            
            actions = ActionChains(driver)
            actions.send_keys_to_element(message_box, Keys.ENTER)
            actions.perform()
            time.sleep(1)
            print(f"[বট উত্তর পাঠিয়েছে]: {text_to_send}")
        except Exception as err:
            try:
                send_btn = driver.find_element(By.XPATH, '//div[@aria-label="Press Enter to send" or @aria-label="Send" or @aria-label="পাঠান"]')
                send_btn.click()
                print(f"[বট উত্তর পাঠিয়েছে (Button Click)]: {text_to_send}")
            except Exception as btn_err:
                print(f"[মেসেজ পাঠাতে সমস্যা]: {err} | {btn_err}")

    def switch_to_unread_chat_and_get_id():
        try:
            chats = driver.find_elements(By.XPATH, '//div[@role="gridcell"]')
            for chat in chats:
                if chat.find_elements(By.XPATH, './/span[contains(@style, "background-color")]') or "m ago" in chat.text or "1m" in chat.text:
                    chat.click()
                    print("\n[📩 নতুন আনরিড চ্যাটে সফলভাবে সুইচ করা হয়েছে!]")
                    time.sleep(3)
                    
                    # বর্তমান চ্যাটটিকে আলাদাভাবে চেনার জন্য কারেন্ট URL বা চ্যাট হেডার টেক্সট ব্যবহার করা যেতে পারে
                    current_url = driver.current_url
                    return current_url
        except Exception as e:
            pass
        return None

    last_replied_message = ""
    start_time = time.time()
    MAX_RUN_TIME = 5 * 60 * 60  # ৫ ঘণ্টা সময়সীমা
    current_chat_id = "default_chat"

    print("\n==================================================")
    print(" Gemini AI বট মেসেজ রিসিভ করার জন্য প্রস্তুত...")
    print("==================================================\n")

    while True:
        if time.time() - start_time > MAX_RUN_TIME:
            print("5 hours completed. Stopping safely for next scheduled restart...")
            break

        try:
            chat_id_detected = switch_to_unread_chat_and_get_id()
            if chat_id_detected:
                current_chat_id = chat_id_detected

            messages = driver.find_elements(By.XPATH, '//div[@role="row"]//div[@dir="auto"] | //div[@dir="auto"]')

            if messages:
                last_element = messages[-1]
                raw_msg = last_element.text.strip()

                if not raw_msg:
                    time.sleep(2)
                    continue

                x_pos = last_element.location["x"]

                # নিজের পাঠানো মেসেজ (ডানপাশের X-pos) ফিল্টার করা
                if x_pos > 550:
                    time.sleep(2)
                    continue

                if raw_msg == last_replied_message:
                    time.sleep(2)
                    continue

                print(f"\n[নতুন ইউজার মেসেজ রিসিভড (চ্যাট আইডি: {current_chat_id[-10:]})]: {raw_msg}")

                # প্রতিটি চ্যাটের জন্য আলাদা সেশন পাস করে উত্তর জেনারেট করা
                ai_reply = generate_ai_response(raw_msg, chat_id=current_chat_id)
                if ai_reply:
                    send_message(ai_reply)
                    last_replied_message = raw_msg
                    time.sleep(3)

        except Exception as loop_error:
            print(f"[লুপ এরর]: {loop_error}")

        time.sleep(2)

except Exception as e:
    print(f"[প্রধান এরর]: {e}")
finally:
    try:
        driver.quit()
    except:
        pass


