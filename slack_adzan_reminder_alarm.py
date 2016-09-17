import json
import os
from datetime import datetime, timedelta
from random import randint

import requests

DATE_FORMAT = '%d-%m-%Y %I:%M %p'

prayer = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

adzan_token = os.getenv('ADZAN_API_KEY')
def parse_adzan(location="yogyakarta"):



    prayer_list, attachment = generate_24_hour_time_adzan(adzan_token, prayer,
                                                          location)

    today_date = datetime.utcnow() + timedelta(hours=7)
    print 'time now ' + str(today_date) + '\n'
    for key, value in prayer_list.items():
        print key + '-' + value
        time_pray = datetime.strptime(value.strip(), DATE_FORMAT)

        if time_pray <= today_date <= time_pray + timedelta(minutes=3):

            text = '<!here|here> Saatnya {0} - {1} untuk daerah {2}'.format(
                key, time_pray, location)

            # only prints sholat schedule when fajr, otherwise empty attachment
            if key != 'fajr':
                attachment = []

            get_random_ayah_attachment(attachment)
            payload = {'channel': '#sholat-reminder', 'username': 'adzan_bot',
                       'text': text, 'attachments': attachment}


            return payload

def get_today_adzan(location="yogyakarta"):
    prayer_list, attachment = generate_24_hour_time_adzan(adzan_token, prayer,
                                                          location)
    text = 'Jadwal Sholat hari ini'
    return text, attachment

def post_adzan(location="yogyakarta"):
    slack_token = os.getenv('SLACK_TOKEN')
    payload = parse_adzan(location)
    slack_post_url = 'https://hooks.slack.com/services/{0}'.format(slack_token)
    requests.post(slack_post_url, data=json.dumps(payload))

def get_random_ayah_attachment(attachment):
    try:
        random_ayah = randint(1, 6236)
        r_arab = requests.get('http://api.globalquran.com/ayah/{'
                              '0}/quran-simple'.format(random_ayah))
        r_terjemah = requests.get('http://api.globalquran.com/ayah/{'
                                  '0}/id.muntakhab'.format(random_ayah))
        quran = r_arab.json()['quran']['quran-simple'][str(random_ayah)]
        lit = r_terjemah.json()['quran']['id.muntakhab'][str(random_ayah)]

        ayah = 'Surah {0} Ayah {1} '.format(quran['surah'], quran['ayah'])
        audio = 'http://audio.globalquran.com/ar.abdulbasitmurattal/mp3' \
                '/64kbs/{0}.mp3'.format(random_ayah)
        fields = []

        fields.append({'title': quran['verse'], 'value': lit['verse']})
        attachment.append(
            {'title': ayah, 'title_link': audio, 'fields': fields,
             'mrkdwn_in': ["text"]})
    except Exception as e:
        print e.message
    print attachment


def generate_24_hour_time_adzan(adzan_token, prayers, location, prayer_day='today'):
    prayer_list = {}
    need_save = True
    day = datetime.utcnow() + timedelta(hours=7)
    input_date = day.strftime('%d-%m-%Y')
    adzan_daily = "Jadwal Sholat tanggal {} untuk wilayah {}".format(
        input_date, location)
    if prayer_day == 'tomorrow' or prayer_day == 'besok':
        day = datetime.utcnow() + timedelta(day=1) + timedelta(hours=7)
    if prayer_day == 'mingguan' or prayer_day == 'weekly':    
        input_date = "weekly/{}".format(input_date)
        adzan_daily = "Jadwal Sholat 7 hari kedepan untuk wilayah {}".format(location)
        need_save = False

    fields = []
    attachment = []
    if os.path.isfile('{}.json'.format(input_date)) and need_save:
        print 'file found'
        with open('{}.json'.format(input_date)) as fp:
            for line in fp:
                prayer_time_line = line.split(';')
                fields.append({"title": prayer_time_line[0].upper(),
                               "value": prayer_time_line[1], "short": True})
                prayer_list[prayer_time_line[0]] = prayer_time_line[1]
        attachment.append(
            {'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})
    else:
        url = os.path.join('http://muslimsalat.com/{0}/'
                           '{1}.json?key={2}'.format(location, input_date,
                                                     adzan_token))
        r = requests.get(url)
        for x in range(0, r.json()['items'].__len__()):
            response_json = r.json()['items'][i]
            print response_json
            if os.path.isfile('{}.json'.format(input_date)):
                with open('{}.json'.format(input_date), 'w'):
                    pass
            else:
                print 'no file found'
            fields =[]
            with open('{}.json'.format(input_date), 'w') as prayer_file:
                for i in prayers:
                    input_time = response_json[i]
                    new_time = datetime.strptime(
                        "{0} {1}".format(input_date, input_time), DATE_FORMAT)
                    prayer_list[i] = new_time.strftime(DATE_FORMAT)
                    fields.append({"title": i,
                               "value": prayer_list[i], "short": True})
                    prayer_file.write('{0};{1}\n'.format(i, prayer_list[i]))
                attachment.append(
            {'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})

    return prayer_list, attachment

def parse_command(command, channel):
    if command[0] == 'adzan':
        return get_adzan_list(command[1])

def get_adzan_list(prayer_day):
    return "Jadwal Sholat", generate_24_hour_time_adzan(adzan_token, prayer,location='yogyakarta',prayer_day='today')


if __name__ == "__main__":
    parse_adzan()
