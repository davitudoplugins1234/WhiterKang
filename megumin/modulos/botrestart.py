import sys
import os

from pyrogram import filters
from pyrogram.types import Message

from megumin import megux

@megux.on_message(filters.command("restart") & filters.user(1715384854))
async def broadcast(c: megux, m: Message):
    await m.reply_text("__Reiniciando aguarde...__")
    args = [sys.executable, "-m", "megumin"]
    os.execl(sys.executable, *args)
