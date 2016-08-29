import json
import os
from datetime import datetime, timedelta

import requests

DATE_FORMAT = '%d-%m-%Y %I:%M %p'

prayer = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


def parse_adzan(location="yogyakarta"):
    slack_token = os.getenv('SLACK_TOKEN')
    adzan_token = os.getenv('ADZAN_API_KEY')

    prayer_list = generate_24_hour_time_adzan(adzan_token, prayer, location)
    today_date = datetime.utcnow() + timedelta(hours=7)
    print 'time now ' + str(today_date) + '\n'
    for key, value in prayer_list.items():
        print key + '-' + value
        time_pray = datetime.strptime(value.strip(), DATE_FORMAT)

        if time_pray <= today_date <= time_pray + timedelta(minutes=3):
            text = '<!here|here> Saatnya {0} - {1} untuk daerah {2}'.format(
                key, time_pray, location)
            slack_post_url = 'https://hooks.slack.com/services/{0}'.format(
                slack_token)

            payload = {'channel': '#sholat-reminder', 'username': 'adzan_bot',
                       'text': text}

            r = requests.post(slack_post_url, data=json.dumps(payload))

            print payload
            break


def generate_24_hour_time_adzan(adzan_token, prayer, location):
    prayer_list = {}
    day = datetime.utcnow() + timedelta(hours=7)
    input_date = day.strftime('%d-%m-%Y')
    if os.path.isfile('{}.json'.format(input_date)):
        print 'file found'
        with open('{}.json'.format(input_date)) as fp:
            for line in fp:
                prayer_time_line = line.split(';')
                prayer_list[prayer_time_line[0]] = prayer_time_line[1]
    else:
        url = os.path.join('http://muslimsalat.com/{0}/'
                           '{1}.json?key={2}'.format(location, input_date,
                                                     adzan_token))
        r = requests.get(url)
        response_json = r.json()['items'][0]
        print 'no file found'
        with open('{}.json'.format(input_date), 'w') as prayer_file:
            for i in prayer:
                input_time = response_json[i]
                new_time = datetime.strptime(
                    "{0} {1}".format(input_date, input_time), DATE_FORMAT)
                prayer_list[i] = new_time.strftime(DATE_FORMAT)
                prayer_file.write('{0};{1}\n'.format(i, prayer_list[i]))
    return prayer_list


if __name__ == "__main__":
    parse_adzan()
