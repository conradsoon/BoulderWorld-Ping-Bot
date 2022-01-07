import sqlite3
import pika
import datetime
import json

with sqlite3.connect('reminders.db') as conn:
    cur = conn.cursor()
# Create table
    cur.execute('''CREATE TABLE IF NOT EXISTS reminders
                   (slot text, id text)''')
    conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', heartbeat=0))
channel = connection.channel()
channel.queue_declare(queue='db_task_queue', durable=True)
channel.queue_declare(queue='reminder_queue', durable=True)

# https://www.rabbitmq.com/tutorials/tutorial-two-python.html
print(' [*] Waiting for messages. To exit press CTRL+C')


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body.decode())
    print(" [x] Done")
    msg = json.loads(body.decode())
    if msg["action"] == "send_ping":
        with sqlite3.connect('reminders.db') as conn:
            cur = conn.cursor()
            for row in cur.execute(f'''SELECT * FROM reminders WHERE slot = \'{msg["timeslot"]}\''''):
                msg = {"action": "remind_id",
                       "timeslot": row[0], "id": row[1]}
                channel.basic_publish(
                    exchange='',
                    routing_key='reminder_queue',
                    body=json.dumps(msg),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                    ))

            conn.commit()

    elif msg["action"] == "set_reminder":
        with sqlite3.connect('reminders.db') as conn:
            cur = conn.cursor()
            # TO-DO: Add check to prevent duplicate reminder
            cur.execute(f'''INSERT INTO reminders(slot, id)
                           VALUES
                           ('{msg["timeslot"]}', '{msg["id"]}')''')
            conn.commit()
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='db_task_queue', on_message_callback=callback)

channel.start_consuming()
