import html
import re
import httpx


from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


def cleanhtml(raw_html):
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext


def escape_definition(definition):
    for key, value in definition.items():
        if isinstance(value, str):
            definition[key] = html.escape(cleanhtml(value))
    return definition
    
    
from megumin import megux 


http = httpx.AsyncClient()


@megux.on_message(filters.command("pypi", prefixes=["/", "!"]))
async def pypi(c: megux, m: Message):
    if len(m.command) == 1:
        return await m.reply_text("pypi_usage")

    text = m.text.split(maxsplit=1)[1]
    r = await http.get(f"https://pypi.org/pypi/{text}/json")
    if r.status_code == 200:
        json = r.json()
        pypi_info = escape_definition(json["info"])

        message = "<b>{package_name}</b> por <i>{author_name} {author_email}</i>\nPlataforma: <b>{platform}</b>\nVersão: <b>{version}</b>\nLicença: <b>{license}</b>\nResumo: <b>{summary}</b>".format(
            package_name=pypi_info["name"],
            author_name=pypi_info["author"],
            author_email=f"&lt;{pypi_info['author_email']}&gt;"
            if pypi_info["author_email"]
            else "",
            platform=pypi_info["platform"] or "Não especificado!",
            version=pypi_info["version"],
            license=pypi_info["license"] or "Não especificado!",
            summary=pypi_info["summary"],
        )

        if pypi_info["home_page"] and pypi_info["home_page"] != "UNKNOWN":
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="package_home_page",
                            url=pypi_info["home_page"],
                        )
                    ]
                ]
            )
        else:
            kb = None
        await m.reply_text(message, disable_web_page_preview=True, reply_markup=kb)
    else:
        await m.reply_text(
            "package_not_found".format(
                package_name=text, http_status=r.status_code
            )
        )
