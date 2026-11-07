# Ahnum Task - FINAL Bot with PERSISTENT SAVE
# Balances, Wallets, Task History, Withdraw History saved to db.json
# Deploy on Render Background Worker: pip install -r requirements.txt / python bot.py

import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime

# ============ CONFIG ============
TOKEN = "8989439425:AAGEb2gLCYEEtz6B2Dx4U595ZM-IsicW2jY"
ADMIN_ID = 8712490852
WHATSAPP_LINK = "https://wa.me/2348000000000"
TELEGRAM_SUPPORT = "@YourSupportUsername"
INVITE_BONUS_NAIRA = 1000
MIN_WITHDRAW_NAIRA = 2000
MIN_WITHDRAW_TON = 1.0
DB_FILE = "db.json"
# ==============================

WALLET_TYPE, CRYPTO_TON, NAIRA_TYPE, NAIRA_NAME, NAIRA_ACC, TASK_SUBMIT_UID, TASK_SUBMIT_PHOTO, WITHDRAW_AMOUNT, WITHDRAW_METHOD = range(9)

users_db = {}
pending_tasks = {}
pending_withdraws = {}
user_approved_count = {}

tasks_db = [
    {"id":1, "title":"Follow on X", "price_ton":"0.5 TON", "price_usdt":"1 USDT", "price_naira":"₦1,500", "desc":"Follow our X account, like and retweet pinned post."},
    {"id":2, "title":"Join Telegram Channel", "price_ton":"0.3 TON", "price_usdt":"0.6 USDT", "price_naira":"₦900", "desc":"Join channel and stay for 24hrs."},
    {"id":3, "title":"Download App & Review", "price_ton":"1 TON", "price_usdt":"2 USDT", "price_naira":"₦3,000", "desc":"Download app, signup, leave review."},
]

# ============ PERSISTENT SAVE / LOAD ============
def save_db():
    try:
        data = {
            "users": {str(k): v for k, v in users_db.items()},
            "tasks": pending_tasks,
            "withdraws": pending_withdraws,
            "counts": {str(k): v for k, v in user_approved_count.items()}
        }
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save failed: {e}")

def load_db():
    global users_db, pending_tasks, pending_withdraws, user_approved_count
    if not os.path.exists(DB_FILE):
        print("No db.json found, starting fresh")
        return
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            # Users: keys back to int
            users_db = {int(k): v for k, v in data.get("users", {}).items()}
            pending_tasks = data.get("tasks", {})
            pending_withdraws = data.get("withdraws", {})
            user_approved_count = {int(k): v for k, v in data.get("counts", {}).items()}
            print(f"Loaded DB: {len(users_db)} users, {len(pending_tasks)} tasks, {len(pending_withdraws)} withdraws")
    except Exception as e:
        print(f"Load failed: {e}")

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"balance_ton":0, "balance_naira":0, "wallets":{}, "invites":0, "referred_by":None}
        save_db()
    return users_db[user_id]

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 ADD WALLET", callback_data="add_wallet")],
        [InlineKeyboardButton("📋 TASK", callback_data="tasks"), InlineKeyboardButton("🎧 CUSTOMER CARE", callback_data="care")],
        [InlineKeyboardButton("👥 INVITE", callback_data="invite")],
        [InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw_start")],
        [InlineKeyboardButton("📜 TASK HISTORY", callback_data="task_history"), InlineKeyboardButton("📜 WITHDRAW HISTORY", callback_data="withdraw_history")]
    ])

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if context.args and context.args[0].startswith("INVITE_"):
        try:
            referrer_id = int(context.args[0].replace("INVITE_",""))
            if referrer_id != update.effective_user.id and user.get("referred_by") is None:
                user["referred_by"] = referrer_id
                save_db()
        except: pass
    text = f"👋 Welcome to *Ahnum Task*\n\n💰 *ACCOUNT BALANCE*\nTON: {user['balance_ton']} TON\nNaira: ₦{user['balance_naira']:,}"
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user = get_user(q.from_user.id)
    text = f"🏠 *Ahnum Task*\n\n💰 *ACCOUNT BALANCE*\nTON: {user['balance_ton']} TON\nNaira: ₦{user['balance_naira']:,}"
    await q.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# ============ WALLET ============
async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 CRYPTO", callback_data="wallet_crypto")],
        [InlineKeyboardButton("₦ NAIRA WALLET", callback_data="wallet_naira")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ])
    await q.edit_message_text("💰 *ADD WALLET*\n\nChoose wallet type:", reply_markup=kb, parse_mode="Markdown")
    return WALLET_TYPE

async def wallet_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("🪙 *CRYPTO - TON ONLY*\n\nPlease send your TON address:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="add_wallet")]]), parse_mode="Markdown")
    return CRYPTO_TON

async def save_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ton = update.message.text.strip()
    if len(ton) < 10:
        await update.message.reply_text("❌ Invalid TON address. Send again:")
        return CRYPTO_TON
    user = get_user(update.effective_user.id)
    user["wallets"]["ton"] = ton
    save_db()
    await update.message.reply_text(f"✅ TON Wallet Saved:\n`{ton}`", reply_markup=main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

async def wallet_naira(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("OPay", callback_data="naira_opay")],
        [InlineKeyboardButton("PalmPay", callback_data="naira_palmpay")],
        [InlineKeyboardButton("⬅️ Back", callback_data="add_wallet")]
    ])
    await q.edit_message_text("₦ *NAIRA WALLET*\n\nChoose bank:", reply_markup=kb, parse_mode="Markdown")
    return NAIRA_TYPE

async def naira_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data["naira_bank"] = "OPay" if q.data == "naira_opay" else "PalmPay"
    await q.edit_message_text(f"₦ *{context.user_data['naira_bank']}*\n\nEnter your full NAME:")
    return NAIRA_NAME

async def naira_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["naira_name"] = update.message.text.strip()
    await update.message.reply_text("Now enter your ACCOUNT NUMBER (exactly 10 numbers):")
    return NAIRA_ACC

async def naira_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc = update.message.text.strip()
    if not acc.isdigit() or len(acc) != 10:
        await update.message.reply_text("❌ Account number must be exactly 10 numbers. Try again:")
        return NAIRA_ACC
    user = get_user(update.effective_user.id)
    bank = context.user_data["naira_bank"]
    name = context.user_data["naira_name"]
    user["wallets"]["naira"] = {"bank": bank, "name": name, "acc": acc}
    save_db()
    await update.message.reply_text(f"✅ *Saved*\nBank: {bank}\nName: {name}\nAccount: {acc}", reply_markup=main_menu(), parse_mode="Markdown")
    return ConversationHandler.END

# ============ TASKS ============
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = []
    for t in tasks_db:
        kb.append([InlineKeyboardButton(f"{t['title']} - {t['price_ton']} / {t['price_naira']}", callback_data=f"task_{t['id']}")])
    kb.append([InlineKeyboardButton("📜 My Task History", callback_data="task_history")])
    kb.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    await q.edit_message_text("📋 *TASKS*\n\nChoose a task:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    tid = int(q.data.replace("task_",""))
    task = next(t for t in tasks_db if t["id"]==tid)
    context.user_data["current_task"] = task
    text = f"📋 *{task['title']}*\n\n{task['desc']}\n\n💰 Price: {task['price_ton']} / {task['price_usdt']} / {task['price_naira']}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ START TASK", callback_data="start_task")],[InlineKeyboardButton("⬅️ Back", callback_data="tasks")]])
    await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    task = context.user_data["current_task"]
    await q.edit_message_text(f"✅ Task Started: *{task['title']}*\n\nAfter completing, send your SCREENSHOT first, then your UID.\n\nPlease send SCREENSHOT now:", parse_mode="Markdown")
    return TASK_SUBMIT_PHOTO

async def task_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["screenshot"] = update.message.photo[-1].file_id
    await update.message.reply_text("Screenshot received ✅\nNow send your UID:")
    return TASK_SUBMIT_UID

async def task_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    task = context.user_data["current_task"]
    user_id = update.effective_user.id
    user = get_user(user_id)
    sub_id = f"{user_id}_{task['id']}_{len(pending_tasks)+1}"
    pending_tasks[sub_id] = {"user_id": user_id, "username": update.effective_user.username or update.effective_user.first_name, "task": task, "uid": uid, "photo_id": context.user_data.get("screenshot"), "status": "pending", "referred_by": user.get("referred_by"), "date": datetime.now().strftime("%d %b %Y, %I:%M %p")}
    save_db()
    await update.message.reply_text(f"✅ *Submitted for Review*\nTask: {task['title']}\nUID: {uid}\n\nWait for admin approval.", reply_markup=main_menu(), parse_mode="Markdown")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{sub_id}"), InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{sub_id}")]])
    caption = f"📥 *NEW SUBMISSION*\n\nUser: @{pending_tasks[sub_id]['username']} (ID: {user_id})\nTask: {task['title']}\nReward: {task['price_ton']} / {task['price_naira']}\nUID: {uid}"
    try:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=context.user_data.get("screenshot"), caption=caption, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        print(e)
    return ConversationHandler.END

# ============ TASK HISTORY ============
async def task_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q = update.callback_query; await q.answer()
        user_id = q.from_user.id
        send_func = q.edit_message_text
    else:
        user_id = update.effective_user.id
        send_func = update.message.reply_text
    my_tasks = [t for t in pending_tasks.values() if t["user_id"] == user_id]
    my_tasks = list(reversed(my_tasks))
    if not my_tasks:
        text = "📜 *TASK HISTORY*\n\nYou have no tasks yet.\n\nTap TASK to start your first task."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Do Task Now", callback_data="tasks")],[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
        await send_func(text, reply_markup=kb, parse_mode="Markdown")
        return
    text = "📜 *TASK HISTORY*\n\n"
    total_approved = 0; total_pending = 0; total_rejected = 0
    for t in my_tasks[:10]:
        if t["status"] == "approved":
            emoji = "✅ APPROVED"; total_approved += 1
        elif t["status"] == "pending":
            emoji = "⏳ PENDING"; total_pending += 1
        else:
            emoji = "❌ REJECTED"; total_rejected += 1
        task = t["task"]
        text += f"{emoji}\nTask: {task['title']}\nReward: {task['price_ton']} / {task['price_naira']}\nUID: {t['uid']}\nDate: {t.get('date','')}\n\n"
    text += f"---\n✅ Approved: {total_approved} | ⏳ Pending: {total_pending} | ❌ Rejected: {total_rejected}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Do New Task", callback_data="tasks")],[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
    await send_func(text, reply_markup=kb, parse_mode="Markdown")

# ============ CUSTOMER CARE ============
async def care(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✈️ TELEGRAM CHAT", url=f"https://t.me/{TELEGRAM_SUPPORT.replace('@','')}")],
        [InlineKeyboardButton("💬 WHATSAPP CHAT", url=WHATSAPP_LINK)],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ])
    await q.edit_message_text("🎧 *CUSTOMER CARE*\n\nHow can we help you?", reply_markup=kb, parse_mode="Markdown")

# ============ INVITE ============
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    user = get_user(uid)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=INVITE_{uid}"
    text = f"👥 *INVITE*\n\nInvite friends & family to complete 2 tasks and earn when their task is approved.\n\n🔗 Your Link:\n`{link}`\n\nFriends Invited: {user['invites']}"
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]]), parse_mode="Markdown")

# ============ WITHDRAW ============
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user = get_user(q.from_user.id)
    ton = user["wallets"].get("ton", "Not saved")
    naira = user["wallets"].get("naira")
    naira_str = f"{naira['bank']} - {naira['name']} - {naira['acc']}" if naira else "Not saved"
    text = f"💸 *WITHDRAW*\n\n💰 Balance:\nTON: {user['balance_ton']} TON\nNaira: ₦{user['balance_naira']:,}\n\n📌 Minimum: {MIN_WITHDRAW_TON} TON / ₦{MIN_WITHDRAW_NAIRA:,}\n\n🪙 TON Wallet: `{ton}`\n₦ Naira Wallet: {naira_str}\n\nEnter amount to withdraw.\nExample: For Naira type `5000`, for TON type `2.5`"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📜 View History", callback_data="withdraw_history")],[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
    await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Enter a valid number. Example: 5000 or 2.5")
        return WITHDRAW_AMOUNT
    context.user_data["withdraw_amount"] = amt
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Withdraw TON", callback_data="wd_ton")],
        [InlineKeyboardButton("₦ Withdraw NAIRA (OPay / PalmPay)", callback_data="wd_naira")],
        [InlineKeyboardButton("⬅️ Cancel", callback_data="home")]
    ])
    await update.message.reply_text(f"Amount: {amt}\n\nChoose withdraw method:", reply_markup=kb)
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    method = "TON" if q.data == "wd_ton" else "NAIRA"
    amt = context.user_data["withdraw_amount"]
    user_id = q.from_user.id
    user = get_user(user_id)
    if method == "TON":
        if "ton" not in user["wallets"]:
            await q.edit_message_text("❌ You have not saved TON wallet. Go to ADD WALLET first.", reply_markup=main_menu())
            return ConversationHandler.END
        if amt < MIN_WITHDRAW_TON:
            await q.edit_message_text(f"❌ Minimum TON withdraw is {MIN_WITHDRAW_TON} TON", reply_markup=main_menu())
            return ConversationHandler.END
        if amt > user["balance_ton"]:
            await q.edit_message_text("❌ Insufficient TON balance.", reply_markup=main_menu())
            return ConversationHandler.END
        wallet_info = user["wallets"]["ton"]
        user["balance_ton"] -= amt
    else:
        if "naira" not in user["wallets"]:
            await q.edit_message_text("❌ You have not saved Naira wallet. Go to ADD WALLET first.", reply_markup=main_menu())
            return ConversationHandler.END
        if amt < MIN_WITHDRAW_NAIRA:
            await q.edit_message_text(f"❌ Minimum Naira withdraw is ₦{MIN_WITHDRAW_NAIRA:,}", reply_markup=main_menu())
            return ConversationHandler.END
        if amt > user["balance_naira"]:
            await q.edit_message_text("❌ Insufficient Naira balance.", reply_markup=main_menu())
            return ConversationHandler.END
        wallet_info = f"{user['wallets']['naira']['bank']} - {user['wallets']['naira']['name']} - {user['wallets']['naira']['acc']}"
        user["balance_naira"] -= amt
    wd_id = f"wd_{user_id}_{len(pending_withdraws)+1}"
    pending_withdraws[wd_id] = {"user_id": user_id, "username": q.from_user.username or q.from_user.first_name, "amount": amt, "method": method, "wallet_info": wallet_info, "status": "pending", "date": datetime.now().strftime("%d %b %Y, %I:%M %p")}
    save_db()
    await q.edit_message_text(f"✅ *Withdraw Request Sent*\n\nAmount: {amt} {method}\nTo: {wallet_info}\nStatus: ⏳ Pending Admin Approval", parse_mode="Markdown", reply_markup=main_menu())
    kb_admin = InlineKeyboardMarkup([[InlineKeyboardButton("✅ PAID / APPROVE", callback_data=f"wd_approve_{wd_id}"), InlineKeyboardButton("❌ REJECT + REFUND", callback_data=f"wd_reject_{wd_id}")]])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"💸 *NEW WITHDRAW REQUEST*\n\nUser: @{pending_withdraws[wd_id]['username']} (ID: {user_id})\nAmount: {amt} {method}\nWallet: {wallet_info}\nDate: {pending_withdraws[wd_id]['date']}\n\nPlease pay and click PAID, or REJECT to refund.", reply_markup=kb_admin, parse_mode="Markdown")
    return ConversationHandler.END

# ============ WITHDRAW HISTORY ============
async def withdraw_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q = update.callback_query; await q.answer()
        user_id = q.from_user.id
        send_func = q.edit_message_text
    else:
        user_id = update.effective_user.id
        send_func = update.message.reply_text
    my_wds = [w for w in pending_withdraws.values() if w["user_id"] == user_id]
    my_wds = list(reversed(my_wds))
    if not my_wds:
        text = "📜 *WITHDRAW HISTORY*\n\nYou have no withdrawals yet.\n\nTap WITHDRAW to make your first withdrawal."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💸 Withdraw Now", callback_data="withdraw_start")],[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
        await send_func(text, reply_markup=kb, parse_mode="Markdown")
        return
    text = "📜 *WITHDRAW HISTORY*\n\n"
    total_paid = 0; total_pending = 0
    for w in my_wds[:10]:
        if w["status"] == "approved":
            emoji = "✅ PAID"; total_paid += w["amount"]
        elif w["status"] == "pending":
            emoji = "⏳ PENDING"; total_pending += w["amount"]
        else:
            emoji = "❌ REJECTED"
        text += f"{emoji}\nAmount: {w['amount']} {w['method']}\nTo: {w['wallet_info']}\nDate: {w.get('date','')}\n\n"
    text += f"---\nTotal Paid: {total_paid}\nTotal Pending: {total_pending}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💸 New Withdraw", callback_data="withdraw_start")],[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
    await send_func(text, reply_markup=kb, parse_mode="Markdown")

# ============ ADMIN - TASKS ============
async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("You are not admin!", show_alert=True); return
    sub_id = q.data.replace("approve_", "")
    sub = pending_tasks.get(sub_id)
    if not sub or sub["status"] != "pending":
        await q.edit_message_caption(caption="Already handled."); return
    sub["status"] = "approved"
    user_id = sub["user_id"]; task = sub["task"]; user = get_user(user_id)
    try:
        naira_amt = int(task["price_naira"].replace("₦","").replace(",","")); user["balance_naira"] += naira_amt
    except: pass
    try:
        ton_amt = float(task["price_ton"].replace("TON","").strip()); user["balance_ton"] += ton_amt
    except: pass
    user_approved_count[user_id] = user_approved_count.get(user_id, 0) + 1
    approved_count = user_approved_count[user_id]
    referred_by = sub.get("referred_by")
    save_db()
    await q.edit_message_caption(caption=f"✅ APPROVED\nUser: @{sub['username']}\nTask: {task['title']}\nUID: {sub['uid']}")
    await context.bot.send_message(chat_id=user_id, text=f"🎉 *Task Approved!*\n\nTask: {task['title']}\nReward added: {task['price_ton']} / {task['price_naira']}\n\nNew Balance: {user['balance_ton']} TON / ₦{user['balance_naira']:,}", parse_mode="Markdown")
    if approved_count == 2 and referred_by:
        referrer = get_user(referred_by)
        referrer["balance_naira"] += INVITE_BONUS_NAIRA; referrer["invites"] += 1
        save_db()
        await context.bot.send_message(chat_id=referred_by, text=f"🎁 *Invite Bonus!*\n\nYour friend @{sub['username']} completed 2 tasks and got approved.\nYou earned ₦{INVITE_BONUS_NAIRA:,} bonus!", parse_mode="Markdown")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("You are not admin!", show_alert=True); return
    sub_id = q.data.replace("reject_", "")
    sub = pending_tasks.get(sub_id)
    if not sub or sub["status"] != "pending":
        await q.edit_message_caption(caption="Already handled."); return
    sub["status"] = "rejected"
    save_db()
    await q.edit_message_caption(caption=f"❌ REJECTED\nUser: @{sub['username']}\nTask: {sub['task']['title']}\nUID: {sub['uid']}")
    await context.bot.send_message(chat_id=sub["user_id"], text=f"❌ *Task Rejected*\n\nTask: {sub['task']['title']}\nReason: Screenshot / UID not valid.\nPlease try again or contact Customer Care.", parse_mode="Markdown")

# ============ ADMIN - WITHDRAW ============
async def wd_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("You are not admin!", show_alert=True); return
    wd_id = q.data.replace("wd_approve_", "")
    wd = pending_withdraws.get(wd_id)
    if not wd or wd["status"] != "pending":
        await q.edit_message_text("Already handled."); return
    wd["status"] = "approved"
    save_db()
    await q.edit_message_text(f"✅ WITHDRAW PAID\nUser: @{wd['username']}\nAmount: {wd['amount']} {wd['method']}\nWallet: {wd['wallet_info']}")
    await context.bot.send_message(chat_id=wd["user_id"], text=f"✅ *Withdraw Approved!*\n\nAmount: {wd['amount']} {wd['method']}\nSent to: {wd['wallet_info']}\n\nCheck your wallet. Thank you for using Ahnum Task.", parse_mode="Markdown")

async def wd_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("You are not admin!", show_alert=True); return
    wd_id = q.data.replace("wd_reject_", "")
    wd = pending_withdraws.get(wd_id)
    if not wd or wd["status"] != "pending":
        await q.edit_message_text("Already handled."); return
    wd["status"] = "rejected"
    user = get_user(wd["user_id"])
    if wd["method"] == "TON":
        user["balance_ton"] += wd["amount"]
    else:
        user["balance_naira"] += wd["amount"]
    save_db()
    await q.edit_message_text(f"❌ WITHDRAW REJECTED + REFUNDED\nUser: @{wd['username']}\nAmount: {wd['amount']} {wd['method']}")
    await context.bot.send_message(chat_id=wd["user_id"], text=f"❌ *Withdraw Rejected*\n\nAmount: {wd['amount']} {wd['method']} has been refunded to your balance.\n\nContact Customer Care for help.", parse_mode="Markdown")

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    pending = [s for s in pending_tasks.values() if s["status"]=="pending"]
    pending_wd = [s for s in pending_withdraws.values() if s["status"]=="pending"]
    if not pending and not pending_wd:
        await update.message.reply_text("No pending submissions.")
        return
    for sub in pending:
        await update.message.reply_text(f"Pending Task: {sub['task']['title']} - @{sub['username']} - UID: {sub['uid']}")
    for wd in pending_wd:
        await update.message.reply_text(f"Pending Withdraw: {wd['amount']} {wd['method']} - @{wd['username']} - {wd['wallet_info']}")

async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    save_db()
    if os.path.exists(DB_FILE):
        await update.message.reply_document(document=open(DB_FILE, "rb"), filename="db.json", caption="Here is your backup - all users, balances, histories")
    else:
        await update.message.reply_text("No backup yet.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=main_menu())
    return ConversationHandler.END

# ============ MAIN ============
def main():
    load_db()
    app = Application.builder().token(TOKEN).build()

    wallet_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_wallet, pattern="^add_wallet$")],
        states={
            WALLET_TYPE: [CallbackQueryHandler(wallet_crypto, pattern="^wallet_crypto$"), CallbackQueryHandler(wallet_naira, pattern="^wallet_naira$")],
            CRYPTO_TON: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ton)],
            NAIRA_TYPE: [CallbackQueryHandler(naira_choose, pattern="^naira_")],
            NAIRA_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, naira_name)],
            NAIRA_ACC: [MessageHandler(filters.TEXT & ~filters.COMMAND, naira_acc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    task_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_task, pattern="^start_task$")],
        states={
            TASK_SUBMIT_PHOTO: [MessageHandler(filters.PHOTO, task_photo)],
            TASK_SUBMIT_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_uid)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_start, pattern="^withdraw_start$")],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WITHDRAW_METHOD: [CallbackQueryHandler(withdraw_method, pattern="^wd_(ton|naira)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("history", withdraw_history))
    app.add_handler(CommandHandler("tasks", task_history))
    app.add_handler(CommandHandler("backup", admin_backup))
    app.add_handler(wallet_conv)
    app.add_handler(task_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(CallbackQueryHandler(show_home, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(list_tasks, pattern="^tasks$"))
    app.add_handler(CallbackQueryHandler(task_detail, pattern="^task_"))
    app.add_handler(CallbackQueryHandler(care, pattern="^care$"))
    app.add_handler(CallbackQueryHandler(invite, pattern="^invite$"))
    app.add_handler(CallbackQueryHandler(task_history, pattern="^task_history$"))
    app.add_handler(CallbackQueryHandler(withdraw_history, pattern="^withdraw_history$"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(wd_admin_approve, pattern="^wd_approve_"))
    app.add_handler(CallbackQueryHandler(wd_admin_reject, pattern="^wd_reject_"))

    print("Bot running... DB loaded")
    app.run_polling()

if __name__ == "__main__":
    main()
