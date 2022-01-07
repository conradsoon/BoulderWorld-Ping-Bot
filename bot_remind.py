from telegram.ext import ExtBot
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
bot = ExtBot(token=bot_token)


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body.decode())
    print(" [x] Done")
    msg = json.loads(body.decode())
    if msg["action"] == "remind_id":
        bot.send_message(chat_id=int(msg["id"]),
                         text=f"Open slot for {msg['timeslot']}!")

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='reminder_queue', on_message_callback=callback)
channel.start_consuming()
