import os
import ast
import json
import re
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from temp_mails import Tenminemail_com
from pyrogram import Client
import requests

# Load environment variables
API_ID = int(os.environ["api_id"])
API_HASH = os.environ["api_hash"]
BOT_TOKEN = os.environ["bot_token"]
CHAT_IDS = ast.literal_eval(os.environ["chat_ids"])
ALL_URLS = ast.literal_eval(os.environ["all_urls"])
EXTRA = os.environ["extra"]
# Pyrogram bot client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
restart = os.environ["restart"]
user = os.environ["user"]
S_SESSIONS = ast.literal_eval(os.environ["st_session"])

# Send result to all chat_ids
async def send_to_all(message: str):
    for chat_id in CHAT_IDS:
        try:
            await app.send_message(chat_id, message)
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

# Main account creation function
async def create_account_async():
    try:
        for attempt in range(10):
            try:
                mail = Tenminemail_com()
                email = mail.email
                break
            except Exception as e:
                if "429" in str(e):
                    print("❌ 429 Rate limit on email. Retrying in 60s...")
                    await asyncio.sleep(60)
                else:
                    raise e
        else:
            return "❌ Error: Email creation failed after 10 retries"

        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        })

        # Step 1-3: Visit initial pages
        s.get(ALL_URLS[0])
        s.get(ALL_URLS[1])
        s.get(ALL_URLS[2])
        csrf_token = s.cookies.get("req_identity")
        s.headers.update({
            "x-csrf-token": csrf_token,
            "accept-language": "en-US,en;q=0.9",
            "x-lang": "en-us"
        })

        # Step 4: Send OTP
        res = s.post(ALL_URLS[3], data=json.dumps({
            "captcha_type": 2,
            "email": email,
            "source": 3,
            "product_id": 14792
        }))

        if res.json().get("code") == 231005:
            return f"BLOCKED|{email}"

        # Step 5: Wait for OTP
        data = mail.wait_for_new_email(delay=1.0, timeout=120)
        if not data:
            return f"[{email}] - ❌ No OTP received"

        content = mail.get_mail_content(data["id"])
        soup = BeautifulSoup(content, "html.parser")
        otp_match = re.search(r"\b\d{6}\b", soup.get_text())
        if not otp_match:
            return f"[{email}] - ❌ OTP not found"

        otp = otp_match.group()

        # Step 6: Validate OTP
        s.post(ALL_URLS[4], data=json.dumps({
            "captcha": otp,
            "captcha_type": 2,
            "email": email
        }))

        # Step 7: Register
        s.post(ALL_URLS[5], data=json.dumps({
            "account_type": 2,
            "email": email,
            "password": "Joker@123",
            "region_type": 1,
            "register_type": 12,
            "lang": "en-US",
            "product_id": 14792,
            "from_web_site": "filmora.wondershare.com",
            "reg_brand": 3,
            "platform_id": None,
            "industry": None,
            "is_login": 1,
            "extra": EXTRA
        }))

        # Save account
        with open("accounts.txt", "a") as f:
            f.write(f"{email} : Joker@123\n")

        return f"[{email}] - ✅ Account created"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# Main runner loop
async def run_forever():
    while True:
        result = await create_account_async()

        if result.startswith("BLOCKED|"):
            email = result.split("|")[1]
            #await send_to_all(f"[{email}] - ❌ Blocked. Sleeping 1h 5s before retry...")
            await send_to_all(f"[{email}] - ❌ Blocked. Restarting Code")
            token = S_SESSIONS[1]
            s = requests.Session()
            s.cookies.update({"streamlit_session": token})
            resp = s.get(user)
            s.headers.update({"x-csrf-token": resp.headers["x-csrf-token"], 'Content-Type': "application/json"})
            s.post(restart)
            #await asyncio.sleep(3605)  # Wait 1 hour + 5 seconds
            
        else:
            await send_to_all(result)
            await asyncio.sleep(5)  # Wait 5 seconds before next run

# Main entry
async def main():
    await app.start()
    await send_to_all("🤖 Bot started and running in loop...")
    try:
        await run_forever()
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
