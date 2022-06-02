import requests 

from pyrogram import filters 
from pyrogram.types import Message 

from megumin import megux, Config
from megumin.utils import get_collection, get_string 
 

@megux.on_message(filters.command("simi", Config.TRIGGER))
async def simi_(_, m: Message):
    text_ = m.text.split(maxsplit=1)[1]
    API = f"https://api.simsimi.net/v2/?text={text_}&lc=pt&cf=false"
    r = requests.get(API).json()  
    if r["success"] in "Eu não resposta. Por favor me ensine.":
        return await m.reply(await get_string(m.chat.id, "SIMI_NO_RESPONSE"))
    if r["success"]:
        return await m.reply(r["success"])
    else:
        return await m.reply(await get_string(m.chat.id, "SIMI_API_OFF"))
