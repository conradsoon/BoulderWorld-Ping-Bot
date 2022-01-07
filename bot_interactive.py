from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.ext import Updater
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from enum import Enum
import json
import os
from datetime import date, time, datetime
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=0))
channel = connection.channel()
channel.queue_declare(queue='db_task_queue', durable=True)
channel.queue_declare(queue='reminder_queue', durable=True)

bot_token = os.environ.get("BWPB_BOT_TOKEN")
updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher

slot_callback_prefix = "slot"
calendar_callback_prefix = "cbcal"


class SlotTypes(Enum):
    WEEKDAY = 1
    WEEKEND = 2
    PH = 3


public_holidays = ["2022-01-01", "2022-02-01", "2022-02-02", "2022-04-15",
                   "2022-05-01", "2022-05-03", "2022-05-15", "2022-07-10", "2022-08-09", "2022-10-24", "2022-12-25"]
public_holidays = [date.fromisoformat(x) for x in public_holidays]
weekday_slots = ["09:00:00", "11:15:00",
                 "13:30:00", "16:00:00", "18:30:00", "21:00:00"]
weekday_slots = [time.fromisoformat(x) for x in weekday_slots]
weekend_slots = ["09:00:00", "11:30:00",
                 "14:00:00", "16:30:00", "19:00:00"]
weekend_slots = [time.fromisoformat(x) for x in weekend_slots]
ph_slots = ["09:00:00", "11:30:00",
            "14:00:00", "16:30:00", "19:00:00"]
ph_slots = [time.fromisoformat(x) for x in ph_slots]


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Set a reminder on which date?")


def set(update: Update, context: CallbackContext):
    calendar, step = DetailedTelegramCalendar().build()
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Select {LSTEP[step]}", reply_markup=calendar)


# good to prevent from selecting previous dates
def calendar_button(update: Update, context: CallbackContext):
    query = update.callback_query
    result, key, step = DetailedTelegramCalendar().process(query.data)
    if not result and key:
        query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)

    elif result:
        # Weekday
        slot_type = SlotTypes.WEEKDAY
        slots = []
        if result in public_holidays:
            slot_type = SlotTypes.PH
            slots = ph_slots
        else:
            if(0 <= result.weekday() <= 4):
                slot_type = SlotTypes.WEEKDAY
                slots = weekday_slots
            else:
                slot_type = SlotTypes.WEEKEND
                slots = weekend_slots
        slots = [datetime.combine(result, slot) for slot in slots]
        keyboard = [[InlineKeyboardButton(
            f"{slot.isoformat()}", callback_data=f"{slot_callback_prefix}_{slot.isoformat()}") for slot in slots]]
        slot_kb = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"You selected {result}, a {slot_type.name} slot.\nPick your slot.", reply_markup=slot_kb)
        # context.bot.send_message(
        #    chat_id=update.effective_chat.id, text=f"You selected {result}, a {slot_type.name} slot")
    query.answer()


def slot_button(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    iso_string = data.split(f"_")[1]
    print(iso_string)
    try:
        date = datetime.fromisoformat(iso_string)
        try:
            msg = {"action": "set_reminder",
                   "timeslot": iso_string, "id": str(update.effective_chat.id)}
            channel.basic_publish(
                exchange='',
                routing_key='db_task_queue',
                body=json.dumps(msg),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ))
            print("Published!")
        except Exception as e:
            print(e)

    except:
        # Catch this later
        print("test")
        query.answer()
    query.answer()
    query.edit_message_text(
        f"Set a reminder for {data}.")


start_handler = CommandHandler('start', start)
set_handler = CommandHandler('set', set)
# https://stackoverflow.com/questions/3143070/javascript-regex-iso-datetime/3143231
slot_button_handler = CallbackQueryHandler(
    slot_button
)
calendar_callback_handler = CallbackQueryHandler(
    calendar_button, pattern="^" + calendar_callback_prefix)


dispatcher.add_handler(start_handler)
dispatcher.add_handler(set_handler)
dispatcher.add_handler(calendar_callback_handler)
dispatcher.add_handler(slot_button_handler)


updater.start_polling()
