import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, is_admin, bot_can_restrict, build_user_mention, extract_user_id
from groups.logs import log_action
from db import get_session
from models import SpecialMember, Tag


def roles_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["special"])
    def special(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(message, "استفاده: /special add|remove|list <reply|user_id>")
        action = parts[1].lower()
        s = get_session()
        try:
            special = [r.user_id for r in s.query(SpecialMember).filter(SpecialMember.chat_id == str(message.chat.id)).all()]
        finally:
            s.close()

        # target via reply or id
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif len(parts) >= 3 and parts[2].lstrip("-").isdigit():
            target_id = int(parts[2])

        if action == "list":
            if not special:
                return bot.reply_to(message, "هیچ ممبر ویژه‌ای ثبت نشده.")
            text = "لیست ممبر ویژه:\n" + "\n".join([f"<code>{uid}</code>" for uid in special])
            return bot.reply_to(message, text, parse_mode="HTML")

        if not target_id:
            return bot.reply_to(message, "کاربر را ریپلای کنید یا id وارد کنید.")

        if action == "add":
            if target_id in special:
                return bot.reply_to(message, "این کاربر قبلا ممبر ویژه است.")
            s = get_session()
            try:
                sm = SpecialMember(chat_id=str(message.chat.id), user_id=target_id)
                s.add(sm)
                s.commit()
            finally:
                s.close()
            try:
                log_action(
                    action="special_add",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target_id,
                )
            except Exception:
                pass
            return bot.reply_to(message, "کاربر به عنوان ممبر ویژه اضافه شد.")

        if action == "remove":
            if target_id not in special:
                return bot.reply_to(message, "این کاربر در لیست ممبر ویژه نیست.")
            s = get_session()
            try:
                s.query(SpecialMember).filter(SpecialMember.chat_id == str(message.chat.id), SpecialMember.user_id == target_id).delete()
                s.commit()
            finally:
                s.close()
            try:
                log_action(
                    action="special_remove",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target_id,
                )
            except Exception:
                pass
            return bot.reply_to(message, "کاربر از ممبر ویژه حذف شد.")

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")


    @bot.message_handler(commands=["tag"])
    def tag(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(message, "استفاده: /tag set|remove|show <reply|user_id> [tag]")
        action = parts[1].lower()
        s = get_session()
        try:
            tags_db = s.query(Tag).filter(Tag.chat_id == str(message.chat.id)).all()
            tags = {str(t.user_id): t.tag for t in tags_db}
        finally:
            s.close()

        # resolve user id
        user_id = None
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        elif len(parts) >= 3 and parts[2].split()[0].lstrip("-").isdigit():
            user_id = int(parts[2].split()[0])

        if action == "show":
            if not user_id:
                return bot.reply_to(message, "کاربر را ریپلای کنید یا id وارد کنید.")
            t = tags.get(str(user_id))
            if not t:
                return bot.reply_to(message, "برای این کاربر تگی ثبت نشده.")
            return bot.reply_to(message, f"Tag: {t}")

        if action == "set":
            # expect: /tag set <reply|user_id> <tag>
            if message.reply_to_message:
                rest = parts[2] if len(parts) >= 3 else ""
                tag_text = rest.strip()
            else:
                # parts[2] should contain "<id> <tag>"
                if len(parts) < 3:
                    return bot.reply_to(message, "پارامترها ناقص‌اند.")
                sub = parts[2].split(maxsplit=1)
                if not sub[0].lstrip("-").isdigit() or len(sub) < 2:
                    return bot.reply_to(message, "استفاده: /tag set <user_id|reply> <tag>")
                user_id = int(sub[0])
                tag_text = sub[1].strip()

            if not user_id or not tag_text:
                return bot.reply_to(message, "کاربر یا تگ نامعتبر است.")
            s = get_session()
            try:
                t = s.query(Tag).filter(Tag.chat_id == str(message.chat.id), Tag.user_id == user_id).first()
                if not t:
                    t = Tag(chat_id=str(message.chat.id), user_id=user_id, tag=tag_text)
                    s.add(t)
                else:
                    t.tag = tag_text
                s.commit()
            finally:
                s.close()
            try:
                log_action(
                    action="tag_set",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=user_id,
                    details=tag_text,
                )
            except Exception:
                pass
            return bot.reply_to(message, "تگ برای کاربر ذخیره شد.")

        if action == "remove":
            if not user_id:
                return bot.reply_to(message, "کاربر را ریپلای کنید یا id وارد کنید.")
            if str(user_id) in tags:
                s = get_session()
                try:
                    s.query(Tag).filter(Tag.chat_id == str(message.chat.id), Tag.user_id == user_id).delete()
                    s.commit()
                finally:
                    s.close()
                try:
                    log_action(
                        action="tag_remove",
                        chat_id=message.chat.id,
                        admin_id=message.from_user.id,
                        target_id=user_id,
                    )
                except Exception:
                    pass
                return bot.reply_to(message, "تگ حذف شد.")
            return bot.reply_to(message, "تگی برای این کاربر وجود ندارد.")

        return bot.reply_to(message, "پارامتر نامعتبر: set|remove|show")


    @bot.message_handler(commands=["promote"])
    def promote(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        # resolve target
        target_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            bot_info = bot.get_me()
            if not bot_can_restrict(bot, message.chat.id, bot_info.id):
                return bot.reply_to(message, "ربات دسترسی کافى برای ارتقا ندارد.")

            # promote with limited rights
            bot.promote_chat_member(
                chat_id=message.chat.id,
                user_id=target_id,
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_invite_users=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_promote_members=False,
            )
            mention = build_user_mention(type("u", (), {"id": target_id, "first_name": str(target_id)}))
            try:
                log_action(
                    action="promote",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target_id,
                )
            except Exception:
                pass
            return bot.reply_to(message, f"کاربر ارتقا یافت: {mention}", parse_mode="HTML")

        except ApiTelegramException as e:
            return bot.reply_to(message, f"خطا هنگام ارتقا: {e}")
