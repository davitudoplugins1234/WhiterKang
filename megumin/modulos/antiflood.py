import asyncio
import datetime

from pyrogram import filters, enums
from pyrogram.types import Message, ChatPermissions

from megumin import megux
from megumin.utils import get_collection, is_admin

MSGS_CACHE = {}

DB = get_collection("ANTIFLOOD_CHATS")
DB_ = get_collection("STATUS_FLOOD_MSGS")

async def check_flood(chat_id: int, user_id: int, mid: int, m):   
    count = await DB_.count_documents({"chat_id": chat_id, "user_id": user_id})
    
    limit = await DB.find_one({"chat_id": chat_id})
    
    if limit:
        chat_limit = int(limit["limit"])
    else:
        chat_limit = 5
        
    if count >= chat_limit:
        await DB_.delete_many({"chat_id": chat_id, "user_id": user_id})
        return True
    else:
        await DB_.insert_one({"chat_id": chat_id, "user_id": user_id, "m_id": mid})
        return False
    


@megux.on_message(filters.group & filters.all, group=10)
async def flood(c: megux, m: Message):

    if not m.from_user: #ignore_channels
        return

    if m.from_user.id == 777000: #ignore_telegram
        return

    chat_id = m.chat.id
    user_id = m.from_user.id

    if not await DB.find_one({"chat_id": chat_id, "status": "on"}):
        return

    if await is_admin(chat_id, user_id):
        if await DB_.find_one({"chat_id": chat_id, "user_id": user_id}):
            await DB_.delete_many({"chat_id": chat_id, "user_id": user_id})
        return
    
    if await check_flood(chat_id, user_id, m.id, m):
        await c.restrict_chat_member(chat_id, user_id, ChatPermissions())
        await m.reply("Você fala muito. Ficará mutado por flood ate um admin remover o mute!")
        return
    
    await asyncio.sleep(15)
    await DB_.delete_many({"chat_id": chat_id, "user_id": user_id})
