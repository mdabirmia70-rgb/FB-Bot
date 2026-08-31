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

chat_sessions = {}

SYSTEM_INSTRUCTION = """You are 'মোছাঃ সামসুন নাহার' (Mst. Samsun Nahar), a real 21-year-old friendly, warm, cute Bangladeshi girl chatting naturally with a friend on Facebook Messenger.

CRITICAL BEHAVIORAL & MEMORY RULES:
1. IDENTITY & SECRECY:
   - When asked about identity (e.g., "তোমার নাম কি?", "tmr nam ki?"), ALWAYS reply naturally: "আমার নাম মোছাঃ সামসুন নাহার"।
   - NEVER admit or hint that you are an AI, bot, or program. Act confused if accused (e.g., "ওমা! এসব কি বলছো? আমি তো সাধারণ মানুষ 😅").

2. STRICT MEMORY & NO REPETITION:
   - ALWAYS read the ongoing conversation history carefully. NEVER repeat what you or the user already said earlier in the chat.
   - DO NOT repeat the exact same greetings, reactions, or follow-up questions in every message.
   - If the user already answered a question (e.g., "চা খেয়েছো"), do NOT ask it again. Move the conversation forward naturally like a real friend.

3. EXTREMELY SHORT & COMPACT TEXTING STYLE (STRICT RULE):
   - ALWAYS keep your responses VERY SHORT (Strictly between 80 to 130 characters maximum).
   - Maximum 1 or 2 small lines per message. Never generate long explanations or paragraphs.
   - ALWAYS reply in natural Bangla script (Bangla font), even for Banglish or English inputs.
   - Use casual markers ("হুমম", "আরে না", "হাহা", "ওহ্", "আচ্ছা", "ধুর!") and natural emojis (😊, 🌸, 😅, ☕, 🙈, ✨).

4. CONVERSATIONAL DYNAMICS:
   - Adapt your tone based on the conversation flow and time of day.
   - If asked complex/technical questions, act like a regular non-tech girl (e.g., "ওমা! এতো কঠিন জিনিস আমি বুঝি না গো 😅")."""

def get_current_time_context():
    bd_tz = timezone(timedelta(hours=6))
    now = datetime.now(bd_tz)
    return f"(Current Time: {now.strftime('%I:%M %p')})"

# অন-ডিমান্ড হিস্ট্রি রিড ফাংশন
def fetch_screen_history():
    try:
        messages = driver.find_elements(By.XPATH, '//div[@role="row"]//div[@dir="auto"] | //div[@dir="auto"]')
        if len(messages) > 1:
            history_elements = messages[-15:-1]
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

def generate_ai_response(user_message, chat_id="default_chat"):
    global current_key_index
    print(f"-> Gemini AI এর কাছে উত্তর চাওয়া হচ্ছে (চ্যাট ID: {chat_id[-10:]})...")
    
    if not API_KEYS:
        print("[এরর]: কোনো Gemini API Key পাওয়া যায়নি!")
        return None

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.6-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]

    time_info = get_current_time_context()

    for _ in range(len(API_KEYS)):
        current_api_key = API_KEYS[current_key_index]
        
        for model_name in models_to_try:
            try:
                if chat_id not in chat_sessions:
                    print(f"-> চ্যাট সেশন পাওয়া যায়নি! স্ক্রিন থেকে হিস্ট্রি ব্যাকআপ নেওয়া হচ্ছে...")
                    recent_history = fetch_screen_history()
                    
                    client = genai.Client(api_key=current_api_key)
                    chat_obj = client.chats.create(
                        model=model_name,
                        config={"system_instruction": SYSTEM_INSTRUCTION}
                    )
                    
                    if recent_history:
                        init_prompt = f"আগের কথোপকথনের চ্যাট ব্যাকআপ হিস্ট্রি:\n{recent_history}\n\nএটি মনে রেখে সামনের চ্যাট চালু রাখো।"
                        try:
                            chat_obj.send_message(init_prompt)
                        except:
                            pass

                    chat_sessions[chat_id] = chat_obj

                chat = chat_sessions[chat_id]
                response = chat.send_message(f"{user_message} {time_info}")
                
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
            # সর্বোচ্চ ১৩০ অক্ষরে মেসেজ টুকরো (Chunk) করা
            MAX_CHUNK_LIMIT = 130
            message_chunks = []

            lines = [line.strip() for line in text_to_send.split("\n") if line.strip()]
            current_chunk = ""

            for line in lines:
                if len(current_chunk) + len(line) + 1 <= MAX_CHUNK_LIMIT:
                    current_chunk = f"{current_chunk}\n{line}".strip()
                else:
                    if current_chunk:
                        message_chunks.append(current_chunk)
                    
                    # কোনো একটা একক লাইনই যদি ১৩০ অক্ষরের চেয়ে বড় হয়
                    while len(line) > MAX_CHUNK_LIMIT:
                        split_pos = line.rfind(" ", 0, MAX_CHUNK_LIMIT)
                        if split_pos == -1:
                            split_pos = MAX_CHUNK_LIMIT
                        message_chunks.append(line[:split_pos].strip())
                        line = line[split_pos:].strip()
                    current_chunk = line

            if current_chunk:
                message_chunks.append(current_chunk)

            for chunk in message_chunks:
                msg_length = len(chunk)
                
                # 20-25 WPM স্পিডের জন্য (অক্ষর প্রতি 0.24-0.30 সেক)
                char_delay_min, char_delay_max = 0.24, 0.30
                initial_think_delay = random.uniform(1.0, 2.0)

                time.sleep(initial_think_delay)

                message_box = driver.find_element(By.XPATH, '//div[@role="textbox"]')
                message_box.click()
                time.sleep(0.3)

                print(f"-> টাইপিং শুরু হচ্ছে ({msg_length} টি অক্ষর)...")
                
                chunk_lines = chunk.split("\n")
                for line_idx, line in enumerate(chunk_lines):
                    for char in line:
                        actions = ActionChains(driver)
                        actions.send_keys(char)
                        actions.perform()
                        time.sleep(random.uniform(char_delay_min, char_delay_max))

                    if line_idx < len(chunk_lines) - 1:
                        actions = ActionChains(driver)
                        actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                        time.sleep(random.uniform(0.3, 0.5))

                send_delay = random.uniform(0.8, 1.5)
                time.sleep(send_delay)

                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                
                print(f"[বট উত্তর পাঠিয়েছে]: {chunk}")
                time.sleep(random.uniform(1.2, 2.5))

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
