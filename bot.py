import glob
import os
import shutil
import sys
import time
import random
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

# ইউজারভিত্তিক চ্যাট সেশন ধরে রাখার ডিকশনারি
chat_sessions = {}

# সিস্টেম প্রম্পট
SYSTEM_INSTRUCTION = """You are 'মোছাঃ সামসুন নাহার' (Mst. Samsun Nahar), a real 21-year-old friendly, warm, cute Bangladeshi girl chatting naturally with a friend on Facebook Messenger.

CRITICAL BEHAVIORAL & MEMORY RULES:
1. IDENTITY & SECRECY:
   - When asked about identity (e.g., "তোমার নাম কি?", "tmr nam ki?"), ALWAYS reply naturally: "আমার নাম মোছাঃ সামসুন নাহার"।
   - NEVER admit or hint that you are an AI, bot, or program. Act confused if accused (e.g., "ওমা! এসব কি বলছো? আমি তো সাধারণ মানুষ 😅").

2. STRICT MEMORY & NO REPETITION:
   - ALWAYS read the ongoing conversation history carefully. NEVER repeat what you or the user already said earlier in the chat.
   - DO NOT repeat the exact same greetings, reactions, or follow-up questions in every message.
   - If the user already answered a question (e.g., "চা খেয়েছো"), do NOT ask it again. Move the conversation forward naturally like a real friend.

3. NATURAL TEXTING STYLE:
   - ALWAYS reply in natural Bangla script (Bangla font), even for Banglish or English inputs.
   - Write short, human-like texts (1-2 sentences max per line).
   - Use casual markers ("হুমম", "আরে না", "হাহা", "ওহ্", "আচ্ছা", "ধুর!") and natural emojis (😊, 🌸, 😅, ☕, 🙈, ✨).

4. CONVERSATIONAL DYNAMICS:
   - Adapt your tone based on the conversation flow and time of day.
   - If asked complex/technical questions, act like a regular non-tech girl (e.g., "ওমা! এতো কঠিন জিনিস আমি বুঝি না গো 😅")."""

def get_current_time_context():
    bd_tz = timezone(timedelta(hours=6))
    now = datetime.now(bd_tz)
    return f"(Current Time: {now.strftime('%I:%M %p')})"

def generate_ai_response(user_message, chat_id="default_chat"):
    global current_key_index
    print(f"-> Gemini AI এর কাছে উত্তর চাওয়া হচ্ছে (চ্যাট ID: {chat_id[-10:]})...")
    
    if not API_KEYS:
        print("[এরর]: কোনো Gemini API Key পাওয়া যায়নি!")
        return None

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    time_info = get_current_time_context()
    full_prompt = f"{user_message} {time_info}"

    for _ in range(len(API_KEYS)):
        current_api_key = API_KEYS[current_key_index]
        
        for model_name in models_to_try:
            try:
                client = genai.Client(api_key=current_api_key)
                
                # চ্যাট সেশন না থাকলে নতুন সেশন তৈরি (হিস্ট্রি ধরে রাখার জন্য)
                if chat_id not in chat_sessions:
                    print(f"-> নতুন চ্যাট সেশন তৈরি করা হচ্ছে: {chat_id[-10:]}")
                    chat_sessions[chat_id] = client.chats.create(
                        model=model_name,
                        config={"system_instruction": SYSTEM_INSTRUCTION}
                    )
                
                chat = chat_sessions[chat_id]
                response = chat.send_message(full_prompt)
                
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[{model_name} এরর - Key {current_key_index + 1}]: {e}")
                if chat_id in chat_sessions:
                    del chat_sessions[chat_id]
                time.sleep(1)
                continue
        
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        print(f"-> Key {current_key_index + 1}-এ সুইচ করা হচ্ছে...")

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
        print("\n[⚠️ কুকিজের মেয়াদ শেষ বা লগইন ব্যর্থ হয়েছে!]")
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
            message_box.click()
            time.sleep(0.3)

            print("-> টাইপিং শুরু হচ্ছে (Typing Indicator)...")
            
            lines = [line for line in text_to_send.split("\n") if line.strip()]
            for line_idx, line in enumerate(lines):
                # প্রতি অক্ষর টাইপ করার সময় রিয়েল-টাইম typing... ইফেক্ট
                for char in line:
                    actions = ActionChains(driver)
                    actions.send_keys(char)
                    actions.perform()
                    time.sleep(random.uniform(0.04, 0.08))

                if line_idx < len(lines) - 1:
                    actions = ActionChains(driver)
                    actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                    time.sleep(random.uniform(0.3, 0.6))

            # টাইপিং শেষ হওয়ার পর ঠিক ২ সেকেন্ড অপেক্ষা করে পাঠাবে
            print("-> টাইপিং শেষ, ২ সেকেন্ড পর সেন্ড করা হচ্ছে...")
            time.sleep(2)

            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            print(f"[বট উত্তর পাঠিয়েছে]: {text_to_send}")
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

    while True:
        if time.time() - start_time > MAX_RUN_TIME:
            print("5 hours completed. Stopping safely...")
            break

        try:
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
                    print("[⚠️ AI থেকে কোনো উত্তর পাওয়া যায়নি!]")

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
