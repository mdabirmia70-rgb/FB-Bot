import time
import requests

# গ্লোবাল স্টেট
is_bot_paused = False
last_processed_update_id = 0

def send_telegram_alert(token, chat_id, message):
    """টেলিগ্রামে সাধারণ টেক্সট মেসেজ পাঠায়"""
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message}
            requests.post(url, json=payload)
            print("[✅ টেলিগ্রামে সতর্কবার্তা পাঠানো হয়েছে!]")
        except Exception as e:
            print(f"[টেলিগ্রাম নোটিফিকেশন এরর]: {e}")

def send_telegram_menu(token, chat_id):
    """টেলিগ্রামে ৩টি ইনলাইন বাটনসহ কন্ট্রোল প্যানেল পাঠায়"""
    if not (token and chat_id):
        return
        
    status_text = "🟢 *অটো-রিপ্লাই চালু আছে*" if not is_bot_paused else "🔴 *অটো-রিপ্লাই বন্ধ আছে*"
    message = f"🤖 *FB Auto-Reply Control Panel*\n\nবর্তমান স্ট্যাটাস: {status_text}"
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Status Check", "callback_data": "status"}],
            [
                {"text": "⏹️ Turn OFF", "callback_data": "off"},
                {"text": "▶️ Turn ON", "callback_data": "on"}
            ]
        ]
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
    """টেলিগ্রাম বাটন ক্লিক এবং ইনকামিং কমান্ড হ্যান্ডেল করে"""
    global is_bot_paused, last_processed_update_id
    if not (token and chat_id):
        return

    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_processed_update_id + 1}&timeout=1"
        res = requests.get(url, timeout=3).json()
        
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                last_processed_update_id = update["update_id"]
                
                # বাটন ক্লিকে রেসপন্স (Callback Query)
                if "callback_query" in update:
                    cb = update["callback_query"]
                    data = cb.get("data")
                    cb_id = cb.get("id")
                    
                    reply_text = ""
                    if data == "status":
                        st = "🔴 বন্ধ (OFF)" if is_bot_paused else "🟢 চালু (ON)"
                        reply_text = f"📊 বট অটো-রিপ্লাই স্ট্যাটাস: {st}"
                    elif data == "off":
                        is_bot_paused = True
                        reply_text = "🔴 অটো-রিপ্লাই সফলভাবে বন্ধ করা হয়েছে!"
                    elif data == "on":
                        is_bot_paused = False
                        reply_text = "🟢 অটো-রিপ্লাই সফলভাবে চালু করা হয়েছে!"

                    # বাটন অ্যালার্ট পপ-আপ
                    requests.post(
                        f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                        json={"callback_query_id": cb_id, "text": reply_text, "show_alert": True}
                    )
                    
                    # আপডেট হওয়া নতুন স্ট্যাটাস প্যানেল পাঠাবে
                    send_telegram_menu(token, chat_id)

                # মেসেজ কমান্ড চেক (/start বা /menu)
                elif "message" in update and "text" in update["message"]:
                    cmd = update["message"]["text"].strip().lower()
                    if cmd in ["/start", "/menu", "menu", "help"]:
                        send_telegram_menu(token, chat_id)
                        
    except Exception as e:
        pass

def get_telegram_reply(token, chat_id, user_msg):
    """API বিজি থাকলে ম্যানুয়াল উত্তরের জন্য ১২০ সেকেন্ড ওয়েট করে"""
    if not (token and chat_id):
        return None

    prompt_text = f"🚨 [API Limit / Busy Alert]\n\nইউজার মেসেজ পাঠিয়েছে:\n\"{user_msg}\"\n\nদয়া করে ১২০ সেকেন্ডের (২ মিনিট) মধ্যে রিপ্লাই দিন।"
    send_telegram_alert(token, chat_id, prompt_text)

    try:
        url_updates = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url_updates).json()
        last_update_id = 0
        if res.get("ok") and res.get("result"):
            last_update_id = res["result"][-1]["update_id"]
    except:
        last_update_id = 0

    print("-> টেলিগ্রাম থেকে ম্যানুয়াল উত্তরের জন্য ১২০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
    start_wait = time.time()

    while time.time() - start_wait < 120:
        try:
            res = requests.get(f"{url_updates}?offset={last_update_id + 1}&timeout=5").json()
            if res.get("ok") and res.get("result"):
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    if str(msg.get("chat", {}).get("id")) == str(chat_id) and "text" in msg:
                        manual_reply = msg["text"].strip()
                        print(f"[✅ টেলিগ্রাম থেকে উত্তর পাওয়া গেছে]: {manual_reply}")
                        send_telegram_alert(token, chat_id, "👍 ম্যানুয়াল উত্তর রিসিভড! মেসেঞ্জারে পাঠানো হচ্ছে...")
                        return manual_reply
        except Exception as e:
            print(f"[টেলিগ্রাম ওয়েট এরর]: {e}")
        time.sleep(2)

    print("[⏰ ১২০ সেকেন্ড শেষ! কোনো রিপ্লাই না পাওয়ায় আবার API-তে ট্রাই করা হচ্ছে...]")
    send_telegram_alert(token, chat_id, "⏰ সময় শেষ! টেলিগ্রাম থেকে উত্তর না পাওয়ায় পুনরায় Gemini API চেষ্টা করা হচ্ছে...")
    return None
