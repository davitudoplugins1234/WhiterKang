from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus, ChatMemberFilter


from megumin import megux 
from megumin.utils import get_collection 


admin_status = [ChatMemberStatus.ADMINISTRATOR or ChatMemberStatus.OWNER]

@megux.on_message(
    (filters.command("report", prefixes=["/", "!"]) | filters.regex("^@admin"))
    & filters.group
    & filters.reply
)
async def report_admins(c: megux, m: Message):
    DISABLED = get_collection(f"DISABLED {m.chat.id}")
    query = "report"
    off = await DISABLED.find_one({"_cmd": query})
    if off:
        return
    if m.reply_to_message.from_user:
        check_admin = await m.chat.get_member(m.reply_to_message.from_user.id)
        if check_admin.status not in admin_status:
            mention = ""
            async for i in m.chat.get_members(filter=ChatMemberFilter.ADMINISTRATORS):
                if not (i.user.is_deleted or i.is_anonymous or i.user.is_bot):
                    mention += f"<a href='tg://user?id={i.user.id}'>\u2063</a>"
            await m.reply_to_message.reply_text(
                "{admins_list}{reported_user} reportado para os administradores.".format(
                    admins_list=mention,
                    reported_user=m.reply_to_message.from_user.mention(),
                ),
            )
