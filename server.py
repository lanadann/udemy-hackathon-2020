import os
import json
import logging
import re
import pycountry
import requests

from flask import Flask, request, make_response, Response

from slack.web.client import WebClient
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier
from slackeventsapi import SlackEventAdapter
from threading import Thread

from language_choices import LANGUAGES
from texttospeech import text_to_wav

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

PRONUNCIATIONS = {}
AUDIO_DICT = {}
SLACK_SIGNING_SECRET = os.environ['SLACK_SIGNING_SECRET']


# -------- helper functions ---------
def input_response(userid, pronunciation, language):
    language_code = LANGUAGES.get(language, 'en')
    audio_file = text_to_wav(text=pronunciation, output_file=userid, code=language_code)
    AUDIO_DICT[userid] = audio_file
    message = "I've updated your pronunciation. Listen to make sure it sounds correct!"

    return audio_file, message

def output_response_user(userid):
    audio_file = AUDIO_DICT.get(userid)
    if not audio_file:
        userName = get_slack_user_name(userid)
        if userName:
            return guess_audio_message(userName, userid, LANGUAGES.get('en'))

    message = "Here's how <@{}> pronounces their name:".format(userid.upper()) if audio_file \
        else "I can't find an audio file for this user."

    return audio_file, message

def output_response_other(word, language):
    audio_file = None
    message = None
    language_code = LANGUAGES.get(language, 'en')
    file_name = "{}-{}".format(language_code, word)
    audio_file = AUDIO_DICT.get(file_name)
    if not audio_file:
        return guess_audio_message(word, file_name, language_code)

    return audio_file, message

def guess_audio_message(name, filename, language_code):
    audio_file = text_to_wav(text=name, output_file=filename, code=language_code)
    AUDIO_DICT[filename] = audio_file
    message = "Here is my guess at pronouncing {}:".format(name)
    return audio_file, message

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
        userid = None
        audio_file = None

        if message.get("subtype") is None:
            command = message.get("text")
            channel_id = message["channel"]
            reply = "Nothing happened :("
            audio_file = None

            pronounce = re.search('.* pronounce (.+)', command.lower())
            record = re.search('my name is pronounced (.+)', command.lower())

            if record:
                userid = message["user"].lower()
                record_in = re.search('my name is pronounced (.+) in (\w+)', command)
                if record_in:
                    pronunciation = record_in.group(1)
                    language = record_in.group(2)
                else:
                    pronunciation = record.group(1)
                    language = 'English'
                audio_file, reply = input_response(userid, pronunciation, language)

            if pronounce:
                pronounce_tag = re.search('<@(.+)>', pronounce.group(1).lower())
                if pronounce_tag:
                    userid = pronounce_tag.group(0).lower()[2:-1]
                    audio_file, reply = output_response_user(userid)
                else:
                    pronounce_in = re.search('.* pronounce (.+) in (\w+)', command)
                    if pronounce_in:
                        pronounce_language = pronounce_in.group(2)
                        audio_file, reply = output_response_other(pronounce_in.group(1), pronounce_language)
                    else:
                        audio_file, reply = output_response_other(pronounce.group(1), 'English')

            slack_client.chat_postMessage(channel=channel_id, text=reply)
            if audio_file:
                try:
                    response = slack_client.files_upload(
                        channels=channel_id,
                        file=audio_file
                    )
                    assert response["file"]
                except SlackApiError as e:
                    print(f"Got an error: {e.response['error']}")

    thread = Thread(target=send_reply, kwargs={"value": event_data})
    thread.start()
    return Response(status=200)


# Get name of slack user from the user ID
def get_slack_user_name(id):
    url = 'https://slack.com/api/users.profile.get'
    params = {
        'token': SLACK_BOT_TOKEN, 'user': id, 'pretty': '1'
    }
    response = requests.get(url, params=params)
    json_data = response.json() if response and response.status_code == 200 else None

    if json_data and 'profile' in json_data:
        if 'real_name' in json_data['profile']:
            return json_data['profile']['real_name']

    return None


# An example of one of your Flask app's routes
@app.route("/")
def event_hook(request):
    json_dict = json.loads(request.body.decode("utf-8"))
    if json_dict["token"] != VERIFICATION_TOKEN:
        return {"status": 403}

    if "type" in json_dict:
        if json_dict["type"] == "url_verification":
            response_dict = {"challenge": json_dict["challenge"]}
            return response_dict
    return {"status": 500}

# Start the Flask server
if __name__ == "__main__":
    """
    You need python 3.6+ to run. Run this command "python server.py"
    You'll also need to use ngrok with the port 5000 and copy/paste the URL here:
    https://api.slack.com/apps/A01C8SP1E30/event-subscriptions
    """
    SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
    SLACK_SIGNATURE = os.environ['SLACK_SIGNATURE']
    VERIFICATION_TOKEN = os.environ['VERIFICATION_TOKEN']

    slack_client = WebClient(SLACK_BOT_TOKEN)
    verifier = SignatureVerifier(SLACK_SIGNATURE)

    app.run()
