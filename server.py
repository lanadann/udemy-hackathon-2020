import os
import json
import logging
import re

from flask import Flask, request, make_response, Response

from slack.web.client import WebClient
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier
from slackeventsapi import SlackEventAdapter
from threading import Thread

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

PRONUNCIATIONS = {}
SLACK_SIGNING_SECRET = os.environ['SLACK_SIGNING_SECRET']

# -------- responses when you talk to the bot --------
slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events", app
)

@slack_events_adapter.on("app_mention")
def handle_message(event_data):
    def send_reply(value):
        event_data = value
        message = event_data["event"]
        print(event_data)
        pronunciation = None
        recording = None

        if message.get("subtype") is None:
            command = message.get("text")
            channel_id = message["channel"]

            pronounce = re.search('.* pronounce <@(.+)>', command.lower())
            if pronounce:
                userid = pronounce.group(1).lower()
                pronunciation = PRONUNCIATIONS.get(userid)
                # TODO: Add default pronounciation using API

            record = re.search('my name is pronounced (.+)', command.lower())
            if record:
                recording = record.group(1)
                PRONUNCIATIONS[message["user"].lower()] = recording
            
            reply = None
            if pronunciation:
                reply = "I found this pronunciation associated with <@{user}>: {pron}".format(user=userid.upper(), pron=pronunciation)
            elif recording:
                reply = "I've updated your pronunciation to: {rec}".format(rec=recording)
            else:
                reply = "I don't understand...sorry! Can you try again?"
            
            slack_client.chat_postMessage(channel=channel_id, text=reply)

    thread = Thread(target=send_reply, kwargs={"value": event_data})
    thread.start()
    return Response(status=200)

# Start the Flask server
if __name__ == "__main__":
    """
    You need python 3.6+ to run. Run this command "python server.py"
    You'll also need to use ngrok with the port 5000 and copy/paste the URL here:
    https://api.slack.com/apps/A01C8SP1E30/event-subscriptions
    """
    SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
    SLACK_SIGNATURE = os.environ['SLACK_SIGNATURE']

    slack_client = WebClient(SLACK_BOT_TOKEN)
    verifier = SignatureVerifier(SLACK_SIGNATURE)

    app.run()
