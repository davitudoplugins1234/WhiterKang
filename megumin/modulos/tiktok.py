import os
from wget import download
import requests 

from pyrogram import filters 
from pyrogram.types import Message

from megumin import megux, Config 

API = "https://hadi-api.herokuapp.com/api/tiktok";

@megux.on_message(filters.command("tdl", Config.TRIGGER))
async def ttdown_(_, message: Message):
    link = input_str(message)
    if not "tiktok.co" in link:
        return await message.edit("`Isso não é um link tiktok`")
    params = {
            "url": link,
        };
    try:
        r = await requests.get(link=API, params=params)
        response = r.json()
    except ValueError:
        return await message.reply("API Inativa")
    if False in response["status"]:
        return await message.reply("Ocorreu um erro ao consultar os dados do video, verifique se você inseriu o link corretamente.")
    msg = await message.reply("📦 <i>Baixando... </i>")
    link_v = response["result"]["video"]["original"]
    vid = download(link_v, Config.DOWN_PATH)
    os.rename(vid, f"{Config.DOWN_PATH}video.mp4")
    await message.reply_document(f"{Config.DOWN_PATH}video.mp4")
    os.remove(f"{Config.DOWN_PATH}video.mp4")
