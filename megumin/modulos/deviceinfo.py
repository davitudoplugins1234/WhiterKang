from pyrogram import filters
from pyrogram.types import Message

from megumin import megux, Config
from megumin.utils import disableable_dec, is_disabled, http
from megumin.utils.decorators import input_str

@megux.on_message(filters.command("deviceinfo", Config.TRIGGER))
@disableable_dec("deviceinfo")
async def deviceinfo(c: megux, m: Message):
    if await is_disabled(m.chat.id, "deviceinfo"):
        return
    if input_str(m):
        name = input_str(m) 
        search = f"{name}".replace(" ", "%")
        get_search_api = (await http.get(f"http://api.davitudo.tk/search/{search}")).json()
        if get_search_api == '[]':
            return await m.reply("<code>Não encontrei esse dispositivo!!</code> <i>:(</i>")        
        id = get_search_api[0]['url']
        img = get_search_api[0]['img']
        link_base = f"http://api.davitudo.tk/device/{id}"
        try:
            get_device_api = (await http.get(link_base)).json()
            name_cll = get_device_api['title']
            await m.reply(f"<b>Foto Device</b>: {img}\n<b>URL Fonte:</b>: https://www.gsmarena.com/{id}\n<b>-Aparelho</b>: {name_cll}", disable_web_page_preview=False)
        except Exception as err:
            return await m.reply("Não consegui obter resultados sobre o aparelho. O gsmarena pode estar offline. <i>Erro</i>: <b>{err}</b>")
    else:
        return await m.reply("Não consigo advinhar o dispositivo!! woobs!!")
