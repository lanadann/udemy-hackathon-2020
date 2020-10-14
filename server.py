import os
import json
import logging

from flask import Flask, request, make_response, Response

from slack.web.client import WebClient
from slack.errors import SlackApiError
from slack.signature import SignatureVerifier

from slashcommand import Slash

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

PRONUNCIATIONS = {}

@app.route("/slack/record_pronunciation", methods=["POST"])
def record_name(): 
  if not verifier.is_valid_request(request.get_data(), request.headers):
    return make_response("invalid request", 403)
  info = request.form
  PRONUNCIATIONS[info["user_name"]] = info["text"]
  print(PRONUNCIATIONS)
#   print(info)
  message = Slash("Just updated your name pronunciation to: {}".format(info["text"]))

  try:
    response = slack_client.chat_postMessage(
      channel='#{}'.format(info["channel_name"]), 
      text=message.getMessage()
    )#.get()
  except SlackApiError as e:
    logging.error('Request to Slack API Failed: {}.'.format(e.response.status_code))
    logging.error(e.response)
    return make_response("", e.response.status_code)

  return make_response("", response.status_code)

@app.route("/slack/get_pronunciation", methods=["POST"])
def get_pronunciation(): 
  if not verifier.is_valid_request(request.get_data(), request.headers):
    return make_response("invalid request", 403)
  info = request.form
#   print(info)
  print(PRONUNCIATIONS)

  requested_user = info["text"].replace("@", "")
  if requested_user in PRONUNCIATIONS:
      message = Slash("Here's how you pronounce @{}'s name: {}".format(requested_user, PRONUNCIATIONS[requested_user]))
  else:
      message = Slash("This user hasn't updated their pronunciation. Maybe try https://www.pronouncenames.com/?")

  try:
    response = slack_client.chat_postMessage(
      channel='#{}'.format(info["channel_name"]), 
      text=message.getMessage()
    )#.get()
  except SlackApiError as e:
    logging.error('Request to Slack API Failed: {}.'.format(e.response.status_code))
    logging.error(e.response)
    return make_response("", e.response.status_code)

  return make_response("", response.status_code)

# Start the Flask server
if __name__ == "__main__":
    """
    You need python 3.6+ to run. Run this command "python server.py"
    You'll also need to use ngrok with the port 5000 and copy/paste the URL here:
    https://api.slack.com/apps/A01C8SP1E30/slash-commands
    """
  SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
  SLACK_SIGNATURE = os.environ['SLACK_SIGNATURE']
  slack_client = WebClient(SLACK_BOT_TOKEN)
  verifier = SignatureVerifier(SLACK_SIGNATURE)

  app.run()
