import os
import ast
import json
import re
import time
import asyncio
from bs4 import BeautifulSoup
from temp_mails import Tenminemail_com
from pyrogram import Client
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests
from datetime import datetime, timedelta

# Load env variables
API_ID = int(os.environ["api_id"])
API_HASH = os.environ["api_hash"]
BOT_TOKEN = os.environ["bot_token"]
CHAT_IDS = ast.literal_eval(os.environ["chat_ids"])
ALL_URLS = ast.literal_eval(os.environ["all_urls"])

# Pyrogram bot client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

executor = ThreadPoolExecutor(max_workers=5)
scheduler = AsyncIOScheduler()

async def send_to_all(message: str):
    for chat_id in CHAT_IDS:
        try:
            await app.send_message(chat_id, message)
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

def create_account_sync():
    try:
        mail = Tenminemail_com()
        email = mail.email

        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        })

        # Step 1–3: Open invite and login pages, fetch CSRF
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
            return f"[{email}] - ❌ Blocked"

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
            "extra": "eyJzaGFyZV9jb2RlIjoiMjhVWXJ5bVpoV20iLCJyZWZlcnJhbF9pZCI6IjQ2NSJ9"
        }))

        # Save account
        with open("accounts.txt", "a") as f:
            f.write(f"{email} : Joker@123\n")

        return f"[{email}] - ✅ Account created"
    except Exception as e:
        return f"❌ Error: {str(e)}"

async def run_accounts():
    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(executor, create_account_sync) for _ in range(5)]
    results = await asyncio.gather(*futures)
    for res in results:
        await send_to_all(res)

def setup_jobs():
    now = datetime.now()
    start_offset = 5  # first run after 5 seconds
    interval = timedelta(hours=1, seconds=10)

    for i in range(24):
        offset = timedelta(seconds=start_offset) + i * interval
        scheduler.add_job(
            run_accounts,
            trigger=IntervalTrigger(start_date=now + offset, hours=1, seconds=10),
            id=f"job_{i}"
        )

async def main():
    await app.start()
    setup_jobs()
    await send_to_all("🤖 Scheduler started successfully!")
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
