#CREDITS https://github.com/ruizlenato/SmudgeLord/blob/rewrite/smudge/plugins/videos.py
import io
import os
import re
import random
import shutil
import tempfile
import datetime
import asyncio
import contextlib
import filetype

from yt_dlp import YoutubeDL
from urllib.parse import unquote
from bs4 import BeautifulSoup

from pyrogram.helpers import ikb
from pyrogram import filters, enums
from pyrogram.errors import BadRequest, FloodWait, Forbidden, MediaEmpty, MessageNotModified, UserNotParticipant
from pyrogram.raw.types import InputMessageID
from pyrogram.raw.functions import channels, messages
from pyrogram.types import Message, CallbackQuery, InputMediaVideo, InputMediaPhoto
from pyrogram.enums import ChatType, ChatAction 


from megumin import megux, Config 
from megumin.utils import humanbytes, tld, csdl, cisdl, tsdl, tisdl, DownloadMedia, extract_info, http, admin_check, check_rights, add_user, find_user


YOUTUBE_REGEX = re.compile(
    r"(?m)http(?:s?):\/\/(?:www\.)?(?:music\.)?youtu(?:be\.com\/(watch\?v=|shorts/|embed/)|\.be\/|)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
)

SDL_REGEX_LINKS = r"(?:htt.+?//)?(?:.+?)?(?:instagram|twitter|tiktok|threads).(com|net)\/(?:\S*)"

TIME_REGEX = re.compile(r"[?&]t=([0-9]+)")

MAX_FILESIZE = 2000000000


@megux.on_message(filters.command("ytdl", Config.TRIGGER))
async def ytdlcmd(c: megux, m: Message):
    user = m.from_user.id

    if not await find_user(user):
        await add_user(user)

    if m.reply_to_message and m.reply_to_message.text:
        url = m.reply_to_message.text
    elif len(m.command) > 1:
        url = m.text.split(None, 1)[1]
    else:
        await m.reply_text(await tld(m.chat.id, "NO_ARGS_YT"))
        return

    ydl = YoutubeDL({"noplaylist": True})

    rege = YOUTUBE_REGEX.match(url)

    t = TIME_REGEX.search(url)
    temp = t.group(1) if t else 0

    if not rege:
        yt = await extract_info(ydl, f"ytsearch:{url}", download=False)
        try:
            yt = yt["entries"][0]
        except IndexError:
            return
    else:
        yt = await extract_info(ydl, rege.group(), download=False)
        
    for f in yt["formats"]:
        with contextlib.suppress(KeyError):
            if f["format_id"] == "140":
                afsize = f["filesize"] or 0
            if f["ext"] == "mp4" and f["filesize"] is not None:
                vfsize = f["filesize"] or 0
                vformat = f["format_id"]

    keyboard = [
        [
            (
                await tld(m.chat.id, "SONG_BNT"),
                f'_aud.{yt["id"]}|{afsize}|{vformat}|{temp}|{user}|{m.id}',
            ),
            (
                await tld(m.chat.id, "VID_BNT"),
                f'_vid.{yt["id"]}|{vfsize}|{vformat}|{temp}|{user}|{m.id}',
            ),
        ]
    ]

    if " - " in yt["title"]:
        performer, title = yt["title"].rsplit(" - ", 1)
    else:
        performer = yt.get("creator") or yt.get("uploader")
        title = yt["title"]

    text = f"🎧 <b>{performer}</b> - <i>{title}</i>\n"
    text += f"💾 <code>{humanbytes(afsize)}</code> (audio) / <code>{humanbytes(int(vfsize))}</code> (video)\n"
    text += f"⏳ <code>{datetime.timedelta(seconds=yt.get('duration'))}</code>"

    await m.reply_text(text, reply_markup=ikb(keyboard))


@megux.on_callback_query(filters.regex("^(_(vid|aud))"))
async def cli_ytdl(c: megux, cq: CallbackQuery):
    try:
        data, fsize, vformat, temp, userid, mid = cq.data.split("|")
    except ValueError:
        return print(cq.data)
    if cq.from_user.id != int(userid):
        return await cq.answer("Isso não é para você...", show_alert=True)
    if int(fsize) > MAX_FILESIZE:
        return await cq.answer(
            await tld(cq.message.chat.id, "YOUTUBE_FILE_BIG"),
            show_alert=True,
            cache_time=60,
        )
    vid = re.sub(r"^\_(vid|aud)\.", "", data)
    url = f"https://www.youtube.com/watch?v={vid}"
    try:
        await cq.message.edit(await tld(cq.message.chat.id, "DOWNLOAD_YT"))
    except MessageNotModified:
        await cq.message.reply_text(await tld(cq.message.chat.id, "DOWNLOAD_YT"))
    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "ytdl")

    ttemp = f"⏰ {datetime.timedelta(seconds=int(temp))} | " if int(temp) else ""
    if "vid" in data:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": f"{vformat}+140",
                "max_filesize": MAX_FILESIZE,
                "noplaylist": True,
            }
        )
    else:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": "bestaudio[ext=m4a]",
                "max_filesize": MAX_FILESIZE,
                "noplaylist": True,
            }
        )
    try:
        yt = await extract_info(ydl, url, download=True)
    except BaseException as e:
        await c.send_log(e)
        await cq.message.edit("<b>Error:</b> <i>{}</i>".format(e))
        return
    try:
        await cq.message.edit(await tld(cq.message.chat.id, "UPLOADING_YT"))
    except MessageNotModified:
        await cq.message.reply_text(await tld(cq.message.chat.id, "UPLOADING_YT"))
    await c.send_chat_action(cq.message.chat.id, enums.ChatAction.UPLOAD_VIDEO)

    filename = ydl.prepare_filename(yt)
    thumb = io.BytesIO((await http.get(yt["thumbnail"])).content)
    thumb.name = "thumbnail.png"
    views = 0
    likes = 0
    if yt.get("view_count"):
        views += yt["view_count"]
    if yt.get("like_count"):
        likes += yt["like_count"]
    if "vid" in data:
        try:
            await c.send_video(
                cq.message.chat.id,
                video=filename,
                width=1920,
                height=1080,
                caption=(await tld(cq.message.chat.id, "YOUTUBE_CAPTION")).format(ttemp + yt["title"], url or "", datetime.timedelta(seconds=yt["duration"]) or 0, yt["channel"] or None, views, likes),
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
            await cq.message.delete()
        except BadRequest as e:
            await c.send_log(e)
            await c.send_message(
                chat_id=cq.message.chat.id,
                text="<b>Error:</b> {errmsg}".format(errmsg=e),
                reply_to_message_id=int(mid),
            )
    else:
        if " - " in yt["title"]:
            performer, title = yt["title"].rsplit(" - ", 1)
        else:
            performer = yt.get("creator") or yt.get("uploader")
            title = yt["title"]
        try:
            await c.send_audio(
                cq.message.chat.id,
                audio=filename,
                title=title,
                performer=performer,
                caption=(await tld(cq.message.chat.id, "YOUTUBE_CAPTION")).format(ttemp + yt["title"], url or "", datetime.timedelta(seconds=yt["duration"]) or 0, yt["channel"] or None, views, likes),
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
        except BadRequest as e:
            await cq.message.edit_text(
                "<b>Error:</b> <i>{errmsg}</i>".format(errmsg=e)
            )
        else:
            await cq.message.delete()

    shutil.rmtree(tempdir, ignore_errors=True)


    
@megux.on_message(filters.command(["dl", "sdl", "mdl"]) | filters.regex(SDL_REGEX_LINKS))
async def sdl(c: megux, message: Message):
    if message.matches:
        if (
            message.chat.type is ChatType.PRIVATE
            or await csdl(message.chat.id)
        ):
            url = message.matches[0].group(0)
        else:
            return None
    elif not message.matches and len(message.command) > 1:
        url = message.text.split(None, 1)[1]
        if not re.match(SDL_REGEX_LINKS, url, re.M):
            return await message.reply_text("This link is not supported use Instagram Links, Tiktok Links, Threads Links, Twitter Links")
    elif message.reply_to_message and message.reply_to_message.text:
        url = message.reply_to_message.text
    else:
        return await message.reply_text(await tld(message.chat.id, "NO_ARGS_YT"))

    if message.chat.type == ChatType.PRIVATE:
        captions = await cisdl(message.from_user.id)
        method = messages.GetMessages(id=[InputMessageID(id=(message.id))])
    else:
        captions = await cisdl(message.chat.id)
        method = channels.GetMessages(
            channel=await c.resolve_peer(message.chat.id),
            id=[InputMessageID(id=(message.id))],
        )

    rawM = (await c.invoke(method)).messages[0].media
    try:
        files, caption = await DownloadMedia().download(url, captions)
    except BaseException as e:
        await asyncio.gather(c.send_err(f"[BaseException]: {e}"))
        return
    except Exception as e:
        await asyncio.gather(c.send_err(f"[Exception]: {e}"))
        return
    
    if len(caption) > 1024:
        caption = caption[:1021] + "..."
    
    medias = []
    for media in files:
        if filetype.is_video(media["p"]) and len(files) == 1:
            await c.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
            return await message.reply_video(
                video=media["p"],
                width=media["h"],
                height=media["h"],
                caption=caption,
            )

        if filetype.is_video(media["p"]):
            if medias:
                medias.append(InputMediaVideo(media["p"], width=media["w"], height=media["h"]))
            else:
                medias.append(
                    InputMediaVideo(
                        media["p"],
                        width=media["w"],
                        height=media["h"],
                        caption=caption,
                    )
                )
        elif not medias:
            medias.append(InputMediaPhoto(media["p"], caption=caption))
        else:
            medias.append(InputMediaPhoto(media["p"]))

    if medias:
        if (
            rawM
            and not re.search(r"(instagram.com/|threads.net)", url)
            and len(medias) == 1
            and "InputMediaPhoto" in str(medias[0])
        ):
            return None

        await c.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)
        await message.reply_media_group(media=medias)
        return None
    return None


@megux.on_callback_query(filters.regex(r"^media_config"))
async def media_config(client: megux, callback: CallbackQuery):
    chat = callback.message.chat
    if chat.type != ChatType.PRIVATE:
        if not await check_rights(chat.id, callback.from_user.id, "can_change_info"):
            return await callback.answer(
                await tld(chat.id, "NO_CHANGEINFO_PERM"), show_alert=True, cache_time=60
            )

    state = ["☑️", "✅"]
    
    if "+" in callback.data and not (await cisdl(chat.id)):
        await tisdl(chat.id, True)
    elif "+" in callback.data and (await cisdl(chat.id)):
        await tisdl(chat.id, False)

    keyboard = [
        [
            (await tld(chat.id, "MEDIAS_CAPTION_BNT"), "media_config"),
            (state[(await cisdl(chat.id))], "media_config+"),
        ],
    ]

    if chat.type != ChatType.PRIVATE:
        if "-" in callback.data and not (await csdl(chat.id)):
            await tsdl(chat.id, True)
        elif "-" in callback.data and (await csdl(chat.id)):
            await tsdl(chat.id, False)

        keyboard += [
            [
                (await tld(chat.id, "AUTO_DOWNLOAD_BNT"), "media_config"),
                (state[(await csdl(chat.id))], "media_config-"),
            ]
        ]

    keyboard += [[(await tld(chat.id, "BACK_BNT"), "config")]]
    return await callback.edit_message_text(
        await tld(chat.id, "MEDIAS_CONFIG_TEXT"), reply_markup=ikb(keyboard)
    )

@megux.on_callback_query(filters.regex(r"config"))
@megux.on_message(filters.command("config"))
async def config(client: megux, union: Message | CallbackQuery):
    reply = union.edit_message_text if isinstance(union, CallbackQuery) else union.reply_text
    chat = union.message.chat if isinstance(union, CallbackQuery) else union.chat

    if chat.type != ChatType.PRIVATE:
        if not await check_rights(chat.id, union.from_user.id, "can_change_info"):
            if isinstance(union, CallbackQuery):
                await union.answer(await tld(chat.id, "NO_CHANGEINFO_PERM"), show_alert=True, cache_time=60)
            else:
                message = await reply(await tld(chat.id, "NO_CHANGEINFO_PERM"))
                await asyncio.sleep(5.0)
                await message.delete()
            return

    keyboard = [
        [
            (await tld(chat.id, "MEDIAS_BNT"), "media_config"),
        ],
        [
            (await tld(chat.id, "button_lang"), "lang_menu"),
        ],
    ]

    await reply(await tld(chat.id, "CONFIG_TEXT"), reply_markup=ikb(keyboard))

