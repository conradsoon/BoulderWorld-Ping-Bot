from datetime import datetime
from telethon import TelegramClient, events
import os
import pika
import json

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
# bw_group_id = -1001409372558 #actual bw id
bw_group_id = 685190053  # test chat id
client = TelegramClient('anon', api_id, api_hash)

cached_timeslots = []

# https://stackoverflow.com/questions/14572020/handling-long-running-tasks-in-pika-rabbitmq
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=0))
channel = connection.channel()
channel.queue_declare(queue='db_task_queue', durable=True)


@client.on(events.NewMessage(chats=bw_group_id))
@client.on(events.MessageEdited(chats=bw_group_id))
async def my_event_handler(event):
    l = event.text.split('\n')
    # Get rids of empty strings
    l = list(filter(None, l))
    # Filters for messages with backtick in front and at back as date-time string.
    l = list(filter(lambda x: x[0] == '`' and x[-1] == '`', l))
    l = [x[1:-1] for x in l]
    l = [x.split(": ") for x in l]
    timeslots = list(filter(lambda x: x[1] != 'FULL', l))
    global cached_timeslots
    for timeslot in timeslots:
        if timeslot[0] not in cached_timeslots:
            slot = datetime.strptime(timeslot[0], "%a %d %b %I:%M %p")
            # this one will not work at end of the year, need special handling
            slot = slot.replace(year=datetime.now().year)
            print(slot)
            msg = {"action": "send_ping",
                   "timeslot": slot.isoformat(), "capacity": timeslot[1]}
            channel.basic_publish(
                exchange='',
                routing_key='db_task_queue',
                body=json.dumps(msg),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ))
            print("Published!")
    cached_timeslots = [x[0] for x in timeslots]
    print(cached_timeslots)

client.start()
client.run_until_disconnected()
