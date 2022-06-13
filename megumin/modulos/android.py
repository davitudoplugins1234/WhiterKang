import rapidjson
import httpx
import asyncio 
import requests

from bs4 import BeautifulSoup

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup


from megumin import megux
from megumin.utils import get_string as tld


http = httpx.AsyncClient()
DEVICE_LIST = "https://raw.githubusercontent.com/androidtrackers/certified-android-devices/master/by_device.json"


@megux.on_message(filters.command(["twrp"], prefixes=["/", "!"]))
async def twrp(c: megux, m: Message):
    if not len(m.command) == 2:
        message = "Por favor, escreva seu codinome nele, ou seja, <code>/twrp herolte</code>"
        await m.reply_text(message)
        return
    device = m.command[1]
    url = await http.get(f"https://eu.dl.twrp.me/{device}/")
    if url.status_code == 404:
        await m.reply_text("TWRP atualmente não está disponível para <code>{}</code>".format(device))
    else:
        message = "<b>Último recovery TWRP para {}</b>\n".format(device)
        page = BeautifulSoup(url.content, "lxml")
        date = page.find("em").text.strip()
        message += "<b>Atualizado em:</b> <code>{}</code>\n".format(date)
        trs = page.find("table").find_all("tr")
        row = 2 if trs[0].find("a").text.endswith("tar") else 1
        for i in range(row):
            download = trs[i].find("a")
            dl_link = f"https://eu.dl.twrp.me{download['href']}"
            dl_file = download.text
            size = trs[i].find("span", {"class": "filesize"}).text
        message += "<b>Tamanho:</b> <code>{}</code>\n".format(size)
        message += "<b>Arquivo:</b> <code>{dl_file.upper()}</code>".format(dl_file.upper())
        keyboard = [[InlineKeyboardButton(text="Download", url=dl_link)]]
        await m.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


@megux.on_message(filters.command(["magisk"], prefixes=["/", "!"]))
async def magisk(c: megux, m: Message):
    repo_url = "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/"
    text = await tld(m.chat.id, "MAGISK_STRING")
    for magisk_type in ["stable", "beta", "canary"]:
        fetch = await http.get(repo_url + magisk_type + ".json")
        data = rapidjson.loads(fetch.content)
        text += (
            f"<b>{magisk_type.capitalize()}</b>:\n"
            f'<a href="{data["magisk"]["link"]}" >Magisk - V{data["magisk"]["version"]}</a>'
            f' | <a href="{data["magisk"]["note"]}" >Changelog</a> \n'
        )
    await m.reply_text(text, disable_web_page_preview=True)


@megux.on_message(filters.command(["device", "whatis"], prefixes=["/", "!"]))
async def device_(_, message: Message):
    if not len(message.command) == 2:
        await message.reply(await tld(message.chat.id, "DEVICE_NO_CODENAME"))
        return
    msg = await message.reply(await tld(message.chat.id, "COM_2"))
    getlist = requests.get(DEVICE_LIST).json()
    target_device = message.text.split()[1].lower()
    if target_device in list(getlist):
        device = getlist.get(target_device)
        text = ""
        for x in device:
            brand = x['brand']
            name = x['name']
            model = x['model']
            text += (await tld(message.chat.id, "DEVICE_SUCCESS")).format(brand, name, model, target_device)
            text += "\n\n"
        await msg.edit(text)
    else:
        await msg.edit((await tld(message.chat.id, "DEVICE_NOT_FOUND")).format(target_device))
        await asyncio.sleep(5)
        await msg.delete()
