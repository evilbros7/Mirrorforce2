import random
import string
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.message_utils import *
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_gdtot_link
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException


def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message

    uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
    uid= f"<a>{update.message.from_user.id}</a>"
    if len(args) > 1:
        link = args[1]
    elif reply_to is not None:
        link = reply_to.text
    else:
        link = ''
    gdtot_link = is_gdtot_link(link)
    if gdtot_link:
        try:
            link = gdtot(link)
        except DirectDownloadLinkException as e:
            return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        gd = gdriveTools.GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            sendMessage(res, context.bot, update)
            return
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "šš¶š¹š²/šš¼š¹š±š²šæ š¶š š®š¹šæš²š®š±š š®šš®š¶š¹š®šÆš¹š² š¶š» ššæš¶šš².\nšš²šæš² š®šæš² ššµš² šš²š®šæš°šµ šæš²ššš¹šš:"
                sendMarkup(msg3, context.bot, update, button)
                if gdtot_link:
                    gd.deletefile(link)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                sendMessage(msg2, context.bot, update)
                return
        if files <= 10:
            msg = sendMessage(f"š² šŖšššššš: <code>{link}</code>", context.bot, update)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
            msgt = f"šš¢šššš„\n\nš¼ššš: {uname}\nš¼ššš š°š«: {uid}\n\nš³ššš šŗššššš:\n<code>{link}</code>"
            sendtextlog(msgt, bot, update)
        else:
            msgtt = f"šš¢šššš„\n\nš¼ššš: {uname}\nš¼ššš š°š«: {uid}\n\nš³ššš šŗššššš:\n<code>{link}</code>"
            sendtextlog(msgtt, bot, update)
            drive = gdriveTools.GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        if update.message.from_user.username:
            uname = f'@{update.message.from_user.username}'
        else:
            uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
        if uname is not None:
            cc = f'\n\nš¾š”š¤š£šš šš®: {uname}'
            men = f'{uname} '
            msg_g = f'\n\n - š½šššš ššššš š¶-š³šššš\n - š½šššš ššššš šøšššš” š»ššš\n - š¹ššš šš³ šš š°ššššš š¶-š³šššš š»ššš'
            fwdpm = f'\n\nššØš® ššš§ šš¢š§š šš©š„šØšš šš§ šš«š¢šÆšš­š šš”šš­ šØš« šš„š¢šš¤ šš®š­š­šØš§ ššš„šØš° š­šØ ššš šš­ š„šØš  šš”šš§š§šš„'
        if button == "cancelled" or button == "":
            sendMessage(men + result, context.bot, update)
        else:
            logmsg = sendLog(result + cc + msg_g, context.bot, update, button)
            if logmsg:
                log_m = f"\n\n<b>Link Uploaded, Click Below Button</b>"
                sendMarkup(result + cc + fwdpm, context.bot, update, InlineKeyboardMarkup([[InlineKeyboardButton(text="ššššš šššš", url=logmsg.link)]]))
                sendPrivate(result + cc + msg_g, context.bot, update, button)
        if gdtot_link:
            gd.deletefile(link)
    else:
        sendMessage('š£šæš¼šš¶š±š² š-ššæš¶šš² š¦šµš®šæš²š®šÆš¹š² šš¶š»šø šš¼ šš¹š¼š»š²', context.bot, update)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
