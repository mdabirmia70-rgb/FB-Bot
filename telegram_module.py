import requests
import time

is_bot_paused = False
last_processed_update_id = 0

def send_telegram_alert(token, chat_id, message):
    if not (token and chat_id):
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[টেলিগ্রাম অ্যালার্ট এরর]: {e}")

def send_telegram_menu(token, chat_id):
    """টেলিগ্রামে ইনপুট বক্সের নিচে আকর্ষণীয় ডিজাইনের Reply Keyboard বাটন পাঠাবে"""
    if not (token and chat_id):
        return
        
    status_text = "🟢 ONLINE (অটো-রিপ্লাই চালু)" if not is_bot_paused else "🔴 OFFLINE (অটো-রিপ্লাই বন্ধ)"
    message = (
        "✨ *FB AUTO-REPLY CONTROL PANEL* ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ *বর্তমান স্ট্যাটাস:* `{status_text}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 _নিচের বাটন চেপে বট সিস্টেম নিয়ন্ত্রণ করুন:_"
    )
    
    # আকর্ষণীয় লুক ও ইমোজি সহ Reply Keyboard বাটন
    keyboard = {
        "keyboard": [
            [{"text": "⚡ BOT STATUS CHECK 📊"}],
            [{"text": "🔴 TURN OFF BOT"}, {"text": "🟢 TURN ON BOT"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[টেলিগ্রাম মেনু এরর]: {e}")

def check_telegram_commands(token, chat_id):
    """টেলিগ্রামের আপডেট হওয়া বাটন প্রেস ও কমান্ড হ্যান্ডেল করবে"""
    global is_bot_paused, last_processed_update_id
    if not (token and chat_id):
        return

    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_processed_update_id + 1}&timeout=1"
        res = requests.get(url, timeout=3).json()
        
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                last_processed_update_id = update["update_id"]
                
                if "message" in update and "text" in update["message"]:
                    msg_text = update["message"]["text"].strip()
                    
                    if "BOT STATUS CHECK" in msg_text or msg_text == "/status":
                        st = "🔴 অফলাইন (OFF)" if is_bot_paused else "🟢 অনলাইন (ON)"
                        send_telegram_alert(token, chat_id, f"📊 *বটের বর্তমান স্ট্যাটাস:* `{st}`")
                        
                    elif "TURN OFF BOT" in msg_text or msg_text == "/off":
                        is_bot_paused = True
                        send_telegram_alert(token, chat_id, "⏹️ *অটো-রিপ্লাই সফলভাবে বন্ধ করা হয়েছে!*")
                        send_telegram_menu(token, chat_id)
                        
                    elif "TURN ON BOT" in msg_text or msg_text == "/on":
                        is_bot_paused = False
                        send_telegram_alert(token, chat_id, "🚀 *অটো-রিপ্লাই সফলভাবে চালু করা হয়েছে!*")
                        send_telegram_menu(token, chat_id)
                        
                    elif msg_text in ["/start", "/menu", "menu", "help"]:
                        send_telegram_menu(token, chat_id)
                        
    except Exception as e:
        pass

def get_telegram_reply(token, chat_id, user_message):
    """API Key এরর হলে টেলিগ্রাম থেকে ম্যানুয়াল উত্তরের জন্য ওয়েট করবে"""
    alert_msg = f"⚠️ [Gemini API Limit Max Out]\n\nইউজারের মেসেজ:\n\"{user_message}\"\n\nদয়া করে এটার উত্তর লিখে পাঠান (১ মিনিটের মধ্যে):"
    send_telegram_alert(token, chat_id, alert_msg)
    
    start_wait = time.time()
    global last_processed_update_id
    
    while time.time() - start_wait < 60:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_processed_update_id + 1}&timeout=2"
            res = requests.get(url, timeout=4).json()
            if res.get("ok") and res.get("result"):
                for update in res["result"]:
                    last_processed_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        if not text.startswith("/"):
                            send_telegram_alert(token, chat_id, f"✅ ম্যানুয়াল উত্তর রিসিভড: {text}")
                            return text
        except Exception as e:
            pass
        time.sleep(2)
        
    return None
