# starterbot's ID as an environment variable
import json
import os

import time
from slackclient import SlackClient

from slack_adzan_reminder_alarm import parse_command, parse_adzan, \
    process_adzan_reminder

BOT_ID = os.getenv("BOT_ID")
AT_BOT = "<@{}>".format(BOT_ID)
# constants
EXAMPLE_COMMAND = "adzan_hari_ini"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.getenv('SLACK_BOT_TOKEN'))


def response_to_command(command, channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    try: 
        attachment = []
        response = "Not sure what you mean. Use the *" + EXAMPLE_COMMAND + \
                   "* command with numbers, delimited by spaces."
        print command
        response,attachment = parse_command(command, channel)
        print response, attachment
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, attachments=attachment, as_user=True)
    except Exception as e:
        print e.message


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            print output

            if 'text' in output and AT_BOT in output['text']:
                print output['text']
                # return text after the @ mention, whitespace removed
                return output['text'].replace(AT_BOT,"").replace(":",
                                                                 "").strip().lower().split(), output['channel']
    return None, None

def process_subscriber():
    try:
        with open('subscriber.json', 'r') as subscriber_file:
            subscriber_data = json.load(subscriber_file)

        for location in subscriber_data:
            response, attachment = process_adzan_reminder(location,60)
            if response:
                for subscriber, value in subscriber_data[location][
                    0].iteritems():
                    if value == "active":
                        slack_client.api_call("chat.postMessage", channel=subscriber,
                                  text=response, attachments=attachment, as_user=True)
    except:
        pass


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        something=True
        print("Adzan_Bot connected and running!")
        while something:
            process_subscriber()
            command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                response_to_command(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")