import os
import json
import time
import re
import ast
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from pyrogram import Client
from pyrogram.methods.utilities.idle import idle
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

API_ID = int(os.environ["api_id"])
API_HASH = os.environ["api_hash"]
BOT_TOKEN = os.environ["bot_token"]
CHAT_IDS = ast.literal_eval(os.environ["chat_ids"])
ALL_URLS = ast.literal_eval(os.environ["all_urls"])
ACCOUNT_PASSWORD =os.environ["acc_pass"]

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

async def send_all(text):
    for chat_id in CHAT_IDS:
        await app.send_message(chat_id=chat_id, text=text)

def create_account_sync():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
    try:
        r = s.post(ALL_URLS[0])
        if r.status_code != 200 or "mailbox" not in r.json():
            return "[❌] Failed to get temp mail."
        j = r.json()
        token, email = j["token"], j["mailbox"]

        s.get(ALL_URLS[1])
        s.get(ALL_URLS[2])
        s.get(ALL_URLS[3])
        csrf = s.cookies.get("req_identity")

        s.headers.update({
            "x-csrf-token": csrf,
            "accept-language": "en-US,en;q=0.9",
            "x-lang": "en-us",
            "Content-Type": "application/json"
        })

        start_time = datetime.now()

        while True:
            r = s.post(ALL_URLS[4], data=json.dumps({
                "captcha_type": 2,
                "email": email,
                "source": 3,
                "product_id": 14792
            }))
            try:
                j = r.json()
            except:
                return f"[{email}] ❌ Error parsing response."
            if j.get("msg") != "limit ip":
                break
            time.sleep(5)

        delta = datetime.now() - start_time

        headersmail = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
            "authorization": "Bearer " + token
        }

        for _ in range(60):
            r = s.get(ALL_URLS[5], headers=headersmail)
            if r.json().get("messages"):
                break
            time.sleep(1)
        else:
            return f"[{email}] ❌ Timeout waiting for OTP email."

        msg_id = r.json()["messages"][0]["_id"]
        r = s.get(f"{ALL_URLS[6]}/{msg_id}", headers=headersmail)
        soup = BeautifulSoup(r.json()["bodyHtml"], "html.parser")
        otp_match = re.search(r"\b\d{6}\b", soup.get_text())

        if not otp_match:
            return f"[{email}] ❌ OTP not found in email."

        otp = otp_match.group()
        s.post(ALL_URLS[7], data=json.dumps({
            "captcha": otp,
            "captcha_type": 2,
            "email": email
        }))

        s.post(ALL_URLS[8], data=json.dumps({
            "account_type": 2,
            "email": email,
            "password": ACCOUNT_PASSWORD,
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

        check = s.get(ALL_URLS[9])
        with open("accounts.txt", "a") as f:
            f.write(f"{email} : {ACCOUNT_PASSWORD}\n")

        return f"[{email}] 🎉 Account created.\nLogin Check: {check.status_code} | {check.json()}"

    except Exception as e:
        return f"[{email}] ❌ Exception: {str(e)}"
    finally:
        s.close()

async def run_accounts():
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = await loop.run_in_executor(None, lambda: [create_account_sync() for _ in range(5)])
    for result in results:
        await send_all(result)

def schedule_jobs():
    for h in range(24):
        scheduler.add_job(run_accounts, CronTrigger(hour=h, second=(5 + 5 * h) % 60))

def setup_jobs():
    for h in range(24):
        scheduler.add_job(run_accounts, CronTrigger(hour=h, second=(5 + 5 * h) % 60))

async def main():
    await app.start()
    scheduler.start()
    setup_jobs()
    await send_all("🤖 Bot started and account creation scheduled.")
    await idle()
    await app.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
