import json
from datetime import datetime, timedelta
from random import randint
import os
import redis
import ast


import operator
import requests

DATE_FORMAT = '%d-%m-%Y %I:%M %p'

prayer = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

adzan_token = os.getenv('ADZAN_API_KEY')
r = redis.from_url(os.environ.get("REDIS_URL"))
def parse_adzan(location="yogyakarta"):

    text, attachment = process_adzan_reminder(location)
    return {'channel': '#sholat-reminder', 'username': 'adzan_bot',
                       'text': text, 'attachments': attachment}


def mark_time_as_done(location, adzan_key, prayer_list):
    day = datetime.utcnow() + timedelta(hours=7)
    input_date = day.strftime('%d-%m-%Y')
    file_name = '{}.json'.format(input_date + "_" + location)
    with open(file_name, 'w') as prayer_file:
        json.dump(prayer_list, prayer_file)




def process_adzan_reminder(location="yogyakarta", range=300):

    prayer_list, attachment = generate_24_hour_time_adzan(adzan_token, prayer,
                                                          location)

    today_date = datetime.utcnow() + timedelta(hours=7)
    for adzan_key, value in sorted(prayer_list.iteritems(),
                                   key=operator.itemgetter(1)):
        time_pray = datetime.strptime(value['time'].strip(), DATE_FORMAT)

        if (time_pray <= today_date <= time_pray + timedelta(seconds=range))\
            and value['status'] == 'active':

            text = '<!here|here> Saatnya {0} - {1} untuk daerah {2}'.format(
                adzan_key, time_pray, location)
            prayer_list[adzan_key]['status']='done'
            mark_time_as_done(location, adzan_key, prayer_list)
            # only prints sholat schedule when fajr, otherwise empty attachment
            if adzan_key != 'fajr':
                attachment = []

            get_random_ayah_attachment(attachment)

            return text, attachment
    return None, []

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
    prayer_time_line ={}

    if prayer_day == 'tomorrow' or prayer_day == 'besok':
        day = day + timedelta(hours=24)
        input_date = day.strftime('%d-%m-%Y')
    if prayer_day == 'mingguan' or prayer_day == 'weekly':    
        need_save = False
    
    fields = []
    attachment = []
    file_name = '{}.json'.format(input_date + "_" + location)
    if need_save and os.path.isfile(file_name):
        adzan_daily = "Tanggal {}".format(input_date)
        with open(file_name) as fp:
            prayer_time_line = json.load(fp)
            for key, value in sorted(prayer_time_line.iteritems(),
                                     key=operator.itemgetter(1)):
                fields.append({"title": key.upper(),
                               "value": value['time'], "short": True})
        attachment.append(
            {'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})
    else:
        path = location
        if not need_save:
            path = location+"/weekly"
        url = os.path.join('http://muslimsalat.com/{0}/'
                           '{1}.json?key={2}'.format(path, input_date,
                                                     adzan_token))
        print url
        r = requests.get(url)
        for x in range(0, r.json()['items'].__len__()):
            response_json = r.json()['items'][x]
            disp_date =  datetime.strptime(response_json['date_for'], '%Y-%m-%d').strftime('%d-%m-%Y')
            adzan_daily = "Tanggal {}".format(disp_date)
            fields =[]
            prayer_time_line = {}
            for i in prayers:
                disp_time = response_json[i]
                new_time = datetime.strptime(
                    "{0} {1}".format(disp_date, disp_time), DATE_FORMAT)
                prayer_list[i] = new_time.strftime(DATE_FORMAT)
                fields.append({"title": i,
                           "value": prayer_list[i], "short": True})
                prayer_time_line[i] = {'time': prayer_list[i], 'status': 'active'}
            attachment.append({'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})
            if need_save:
                with open(file_name, 'w') as prayer_file:
                    json.dump(prayer_time_line, prayer_file)

    return prayer_time_line, attachment


def add_subscriber(command, channel):

    if command.__len__() >= 2:
        location = command[1]
        print "subscribing to ".format(location)
        subscriber_data = None
        response = ""
        try:
            subscriber_data = ast.literal_eval(r.get("subscriber"))
            print "subscriber {}".format(str(subscriber_data))
        except Exception as e:
            print e.message
            print "read failed"

        if subscriber_data is None:
            subscriber_data = {location:[{}]}
        elif not location in subscriber_data:
            subscriber_data[location] = [{}]

        subscriber_location_data = subscriber_data[location][0]

        if channel in subscriber_location_data:
            response = "Already subscribed to {}".format(location)
        else:
            subscriber_location_data[channel] = "active"
            response = "Successfully subscribed to {}".format(location)
        subscriber_data[location][0] = subscriber_location_data

        r.set("subscriber",subscriber_data)
        return response, []


def get_subscriber():
    try:
        return ast.literal_eval(r.get("subscriber"))
    except:
        return "no subscriber data"


def parse_command(command, channel):
    try: 
        if command[0] == 'adzan':
            location = 'yogyakarta'
            if command.__len__() > 2:
                location = command[2]
            return get_adzan_list(command[1], location)
        elif command[0] == 'subscribe':
            return add_subscriber(command,channel)
    except Exception as e:
        print e.message


def get_adzan_list(prayer_day,location):
    return "Jadwal Sholat untuk wilayah {}".format(location), generate_24_hour_time_adzan(adzan_token, prayer,location,prayer_day)[1]

if __name__ == "__main__":
    print add_subscriber("","")
