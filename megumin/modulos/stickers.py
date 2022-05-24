import os
import shutil
import tempfile
import asyncio
import ffmpeg
import re
import math
import httpx


from PIL import Image


from pyrogram import filters, emoji, enums
from pyrogram.errors import PeerIdInvalid, StickersetInvalid
from pyrogram.raw.functions.messages import GetStickerSet, SendMedia
from pyrogram.raw.functions.stickers import AddStickerToSet, CreateStickerSet
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from typing import Tuple, Callable
from functools import wraps, partial
from pyrogram.raw.types import (
    DocumentAttributeFilename,
    InputDocument,
    InputMediaUploadedDocument,
    InputStickerSetItem,
    InputStickerSetShortName,
)


def get_emoji_regex():
    e_list = [
        getattr(emoji, e).encode("unicode-escape").decode("ASCII")
        for e in dir(emoji)
        if not e.startswith("_")
    ]
    # to avoid re.error excluding char that start with '*'
    e_sort = sorted([x for x in e_list if not x.startswith("*")], reverse=True)
    # Sort emojis by length to make sure multi-character emojis are
    # matched first
    pattern_ = f"({'|'.join(e_sort)})"
    return re.compile(pattern_)


EMOJI_PATTERN = get_emoji_regex()


SUPPORTED_TYPES = ["jpeg", "png", "webp"]
http = httpx.AsyncClient()


from megumin import megux, Config
from megumin.utils import get_collection, get_string 


CHAT_LOGS = Config.GP_LOGS 


@megux.on_message(filters.command(["getsticker"], prefixes=["/", "!"]))
async def getsticker_(c: megux, m: Message):
    DISABLED = get_collection(f"DISABLED {m.chat.id}")
    query = "getsticker"  
    off = await DISABLED.find_one({"_cmd": query})
    if off:
        return
    sticker = m.reply_to_message.sticker

    if sticker:
        if sticker.is_animated:
            await m.reply_text("Sticker animado não é suportado!")
        elif not sticker.is_animated:
            with tempfile.TemporaryDirectory() as tempdir:
                path = os.path.join(tempdir, "getsticker")
            sticker_file = await c.download_media(
                message=m.reply_to_message,
                file_name=f"{path}/{sticker.set_name}.png",
            )
            await m.reply_to_message.reply_document(
                document=sticker_file,
                caption=(
                    f"<b>Emoji:</b> {sticker.emoji}\n"
                    f"<b>Sticker ID:</b> <code>{sticker.file_id}</code>\n\n"
                    f"<b>Send by:</b> @WhiterKangBOT"
                ),
            )
            shutil.rmtree(tempdir, ignore_errors=True)
    else:
        await m.reply_text("Isso não é um sticker!")


@megux.on_message(filters.command("stickerid", prefixes=["/", "!"]) & filters.reply)
async def getstickerid(c: megux, m: Message):
    DISABLED = get_collection(f"DISABLED {m.chat.id}")
    query = "stickerid"  
    off = await DISABLED.find_one({"_cmd": query})
    if off:
        return
    if m.reply_to_message.sticker:
        await m.reply_text(
            "O id deste sticker é: <code>{stickerid}</code>".format(
                stickerid=m.reply_to_message.sticker.file_id
            )
        )


@megux.on_message(filters.command(["kibe", "kang"], prefixes=["/", "!"]))
async def kang_sticker(c: megux, m: Message):
    DISABLED = get_collection(f"DISABLED {m.chat.id}")
    query = "kang"  
    off = await DISABLED.find_one({"_cmd": query})
    if off:
        return
    prog_msg = await m.reply_text(await get_string(m.chat.id, "KANGING"))
    try:
        user = await c.get_me()
    except FloodWait as e:
        await asyncio.sleep(e.value)
    bot_username = user.username
    sticker_emoji = "🤔"
    packnum = 0
    packname_found = False
    resize = False
    animated = False
    videos = False
    convert = False
    reply = m.reply_to_message
    user = await c.resolve_peer(m.from_user.username or m.from_user.id)

    if reply and reply.media:
        if reply.photo:
            resize = True
        elif reply.animation:
            videos = True
            convert = True
        elif reply.video:
            convert = True
            videos = True
        elif reply.document:
            if "image" in reply.document.mime_type:
                # mime_type: image/webp
                resize = True
            elif enums.MessageMediaType.VIDEO == reply.document.mime_type:
                # mime_type: application/video
                videos = True
                convert = True
            elif enums.MessageMediaType.ANIMATION == reply.document.mime_type:
                # mime_type: video/mp4
                videos = True
                convert = True
            elif "tgsticker" in reply.document.mime_type:
                # mime_type: application/x-tgsticker
                animated = True
        elif reply.sticker:
            if not reply.sticker.file_name:
                return await prog_msg.edit_text(
                    await get_string(m.chat.id, "STICKER_NOT_NAME")
                )
            if reply.sticker.emoji:
                sticker_emoji = reply.sticker.emoji
            animated = reply.sticker.is_animated
            videos = reply.sticker.is_video
            if videos:
                convert = False
            else:
                if not reply.sticker.file_name.endswith(".tgs"):
                    resize = True
        else:
            return await prog_msg.edit_text(
                await get_string(m.chat.id, "NO_STICKER_SUPORTED")
            )

        pack_prefix = "anim" if animated else "vid" if videos else "a"
        packname = f"{pack_prefix}_{m.from_user.id}_by_{bot_username}"

        if len(m.command) > 1:
            if m.command[1].isdigit() and int(m.command[1]) > 0:
                # provide pack number to kang in desired pack
                packnum = m.command.pop(1)
                packname = f"{pack_prefix}{packnum}_{m.from_user.id}_by_{bot_username}"
            if len(m.command) > 1:
                # matches all valid emojis in input
                sticker_emoji = (
                    "".join(set(EMOJI_PATTERN.findall("".join(m.command[1:]))))
                    or sticker_emoji
                )
        filename = await c.download_media(m.reply_to_message)
        if not filename:
            # Failed to download
            await prog_msg.delete()
            return
    elif m.entities and len(m.entities) > 1:
        packname = f"c{m.from_user.id}_by_{bot_username}"
        pack_prefix = "a"
        # searching if image_url is given
        img_url = None
        filename = "sticker.png"
        for y in m.entities:
            if y.type == "url":
                img_url = m.text[y.offset : (y.offset + y.length)]
                break
        if not img_url:
            await prog_msg.delete()
            return
        try:
            r = await http.get(img_url)
            if r.status_code == 200:
                with open(filename, mode="wb") as f:
                    f.write(r.read())
        except Exception as r_e:
            return await prog_msg.edit_text(f"{r_e.__class__.__name__} : {r_e}")
        if len(m.command) > 2:
            # m.command[1] is image_url
            if m.command[2].isdigit() and int(m.command[2]) > 0:
                packnum = m.command.pop(2)
                packname = f"a{packnum}_{m.from_user.id}_by_{bot_username}"
            if len(m.command) > 2:
                sticker_emoji = (
                    "".join(set(EMOJI_PATTERN.findall("".join(m.command[2:]))))
                    or sticker_emoji
                )
            resize = True
    else:
        return await prog_msg.edit_text(await get_string(m.chat.id, "STICKER_NO_REPLY"))
    try:
        if resize:
            filename = resize_image(filename)
        elif convert:
            filename = await convert_video(filename)
            if filename is False:
                return await prog_msg.edit_text("Error")
        max_stickers = 50 if animated else 120
        while not packname_found:
            try:
                stickerset = await c.invoke(
                    GetStickerSet(
                        stickerset=InputStickerSetShortName(short_name=packname),
                        hash=0,
                    )
                )
                if stickerset.set.count >= max_stickers:
                    packnum += 1
                    packname = (
                        f"{pack_prefix}_{packnum}_{m.from_user.id}_by_{bot_username}"
                    )
                else:
                    packname_found = True
            except StickersetInvalid:
                break
        file = await c.save_file(filename)
        media = await c.invoke(
            SendMedia(
                peer=(await c.resolve_peer(CHAT_LOGS)),
                media=InputMediaUploadedDocument(
                    file=file,
                    mime_type=c.guess_mime_type(filename),
                    attributes=[DocumentAttributeFilename(file_name=filename)],
                ),
                message=f"#Sticker kang by UserID -> {m.from_user.id}",
                random_id=c.rnd_id(),
            ),
        )
        msg_ = media.updates[-1].message
        stkr_file = msg_.media.document
        if packname_found:
            await prog_msg.edit_text(await get_string(m.chat.id, "USE_EXISTING_PACK"))
            await c.invoke(
                AddStickerToSet(
                    stickerset=InputStickerSetShortName(short_name=packname),
                    sticker=InputStickerSetItem(
                        document=InputDocument(
                            id=stkr_file.id,
                            access_hash=stkr_file.access_hash,
                            file_reference=stkr_file.file_reference,
                        ),
                        emoji=sticker_emoji,
                    ),
                )
            )
        else:
            await prog_msg.edit_text(await get_string(m.chat.id, "CREATE_STICKER_PACK"))
            stkr_title = f"{m.from_user.first_name[:32]}'s "
            if animated:
                stkr_title += "WhiterKang AnimPack"
            elif videos:
                stkr_title += "WhiterKang VidPack"
            if packnum != 0:
                stkr_title += f" v{packnum}"
            try:
                await c.invoke(
                    CreateStickerSet(
                        user_id=user,
                        title=stkr_title,
                        short_name=packname,
                        stickers=[
                            InputStickerSetItem(
                                document=InputDocument(
                                    id=stkr_file.id,
                                    access_hash=stkr_file.access_hash,
                                    file_reference=stkr_file.file_reference,
                                ),
                                emoji=sticker_emoji,
                            )
                        ],
                        animated=animated,
                        videos=videos,
                    )
                )
            except PeerIdInvalid:
                return await prog_msg.edit_text(
                    await get_string(m.chat.id, "STICKERS_NOT_FOUND_USER"),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "/start", url=f"https://t.me/{bot_username}?start"
                                )
                            ]
                        ]
                    ),
                )

    except Exception as all_e:
        await prog_msg.edit_text(f"{all_e.__class__.__name__} : {all_e}")
    else:
        await prog_msg.edit_text(
            (await get_string(m.chat.id, "STICKERS_KANGED")).format(packname, sticker_emoji)
        )
        # Cleanup
        await c.delete_messages(chat_id=CHAT_LOGS, message_ids=msg_.id, revoke=True)
        try:
            os.remove(filename)
        except OSError:
            pass


def resize_image(filename: str) -> str:
    im = Image.open(filename)
    maxsize = 512
    scale = maxsize / max(im.width, im.height)
    sizenew = (int(im.width * scale), int(im.height * scale))
    im = im.resize(sizenew, Image.NEAREST)
    downpath, f_name = os.path.split(filename)
    # not hardcoding png_image as "sticker.png"
    png_image = os.path.join(downpath, f"{f_name.split('.', 1)[0]}.png")
    im.save(png_image, "PNG")
    if png_image != filename:
        os.remove(filename)
    return png_image


async def convert_video(filename: str) -> str:
    downpath, f_name = os.path.split(filename)
    webm_video = os.path.join(downpath, f"{f_name.split('.', 1)[0]}.webm")
    cmd = [
        "ffmpeg",
        "-loglevel",
        "quiet",
        "-i",
        filename,
        "-t",
        "00:00:03",
        "-vf",
        "fps=30",
        "-c:v",
        "vp9",
        "-b:v:",
        "500k",
        "-preset",
        "ultrafast",
        "-s",
        "512x512",
        "-y",
        webm_video,
    ]

    proc = await asyncio.create_subprocess_exec(*cmd)
    # Wait for the subprocess to finish
    await proc.communicate()

    if webm_video != filename:
        os.remove(filename)
    return webm_video
