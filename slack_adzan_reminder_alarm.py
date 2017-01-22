import json
from datetime import datetime, timedelta
import datetime as date_time
from random import randint
import os
import redis
import ast


import operator
import requests
from geopy import Nominatim
from iclib import salat

DATE_THRESHOLD = "20170113"

DATE_FORMAT = '%d-%m-%Y %H:%M:%S'

prayer = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

adzan_token = os.getenv('ADZAN_API_KEY')
redis_db = redis.from_url(os.environ.get("REDIS_URL"))


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
        if adzan_key != 'title':
            time_pray = datetime.strptime(value['time'].strip(), DATE_FORMAT)
            if (time_pray <= today_date <= time_pray + timedelta(seconds=range))\
                and value['status'] == 'active':

                text = '<!here|here> Saatnya {0} - {1} untuk daerah {2}'.format(
                    adzan_key, time_pray, prayer_list['title'])
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

        day = datetime.utcnow() + timedelta(hours=7)
        threshold =  datetime.strptime(DATE_THRESHOLD, '%Y%m%d')
        random_ayah = 1 if int((day - threshold).days) % 6236 == 0 else \
            int((day - threshold).days) + 1
        print random_ayah
        r_all = requests.get('http://api.alquran.cloud/ayah/{0}/'
                             'editions/quran-simple,id.indonesian'
                             .format(random_ayah))
        quran_response = r_all.json()['data']
        print quran_response
        surah_ = quran_response[0]['surah']
        print surah_

        surah_name =  "{0} ({1}) type {2}".format(surah_['englishName'],surah_['englishNameTranslation'],surah_['revelationType'] )
        print surah_name
        num_of_ayah = surah_['numberOfAyahs']
        print num_of_ayah
        cur_ayah = quran_response[0]['numberInSurah']
        print cur_ayah
        quran = quran_response[0]['text']
        print quran
        lit = str(quran_response[1]['text'])
        # r_arab = requests.get('http://api.globalquran.com/ayah/{'
        #                       '0}/quran-simple'.format(random_ayah))
        # print r_arab
        # r_terjemah = requests.get('http://api.globalquran.com/ayah/{'
        #                           '0}/id.muntakhab'.format(random_ayah))
        # quran = r_arab.json()['quran']['quran-simple'][str(random_ayah)]
        # lit = r_terjemah.json()['quran']['id.muntakhab'][str(random_ayah)]

        ayah = '[ODOA] Surah {0} Ayah {1} of {2} '.format(str(surah_name),
                                                   str(cur_ayah), str(num_of_ayah))
        audio = 'http://audio.globalquran.com/ar.abdulbasitmurattal/mp3' \
                '/64kbs/{0}.mp3'.format(random_ayah)
        fields = []
        print quran
        fields.append({"title": quran, "value": lit})
        attachment.append(
            {"title": ayah, "title_link": audio, "fields": fields,
             "mrkdwn_in": ["text"]})
    except Exception as e:
        print e.message
    print attachment
    return attachment


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
        with open(file_name) as fp:
            prayer_time_line = json.load(fp)
            # adzan_daily = prayer_time_line['title']
            adzan_daily =prayer_time_line['title']
            for key, value in sorted(prayer_time_line.iteritems(),
                                     key=operator.itemgetter(1)):
                if key != 'title':
                    fields.append({"title": key.upper(),
                               "value": value['time'], "short": True})
        attachment.append(
            {'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})
    else:
        path = location
        if not need_save:
            path = location+"/weekly"
        try:
            geolocator = Nominatim()
            geo_location = geolocator.geocode(location)
            if geo_location is None:
                raise Exception("")
            else:
                c = (salat.TimeCalculator().date(day)

                    # latitude, longitude, altitude/height, timezone
                    .location(geo_location.latitude, geo_location.longitude,
                              geo_location.altitude, +7)
                    .method('muhammadiyah'))
                t = c.calculate()
                prayer_time_line = {}
                adzan_daily = "{0}".format(geo_location._address)
                prayer_time_line['title'] = adzan_daily
                adzan_daily = "Jadwal Sholat Tanggal {0} untuk ".format(
                    input_date) + adzan_daily
                fields =[]
                for i in range (0, t._names.__len__()):
                    pray_time = t.get_hm(i)
                    lst = list(pray_time)
                    if lst[0] >= 24:
                        lst[0] = lst[0] - 24
                    pray_time = tuple(lst)
                    new_time = datetime.strptime(
                        "{0} {1}".format(input_date, str(date_time.time(*pray_time))),
                        DATE_FORMAT)
                    # workaround for the issue in asr

                    fields.append({"title": t._names[i],
                               "value": new_time.strftime(DATE_FORMAT), "short": True})
                    prayer_time_line[t._names[i]] = {'time': new_time.strftime(DATE_FORMAT), 'status': 'active'}

                attachment.append({'title': adzan_daily, 'fields': fields, 'mrkdwn_in': ["text"]})
                if need_save:
                    with open(file_name, 'w') as prayer_file:
                        json.dump(prayer_time_line, prayer_file)
        except:
            raise LookupError("Unable to find location {} or the "
                              "keyword not found".format(location))

    return prayer_time_line, attachment


def force_set_subscriber(command, channel):

    if command.__len__() >= 2:
        location = command[1]
        new_channel = str(command[2]).split(",")
        print "subscribing to {}".format(location)
        subscriber_data = None
        response = ""
        try:
            subscriber_data = ast.literal_eval(redis_db.get("subscriber"))
            print "subscriber {}".format(str(subscriber_data))
        except LookupError as le:
            response = le.message
            return response, []
        except Exception as e:
            print e.message
            print "read failed"

        subscriber_data[location] = [{}]
        subscriber_location_data = subscriber_data[location][0]

        for new_ch in new_channel:
            subscriber_location_data[new_ch.upper()] = "active"
            response = "Successfully subscribed to {}".format(location)
        subscriber_data[location][0] = subscriber_location_data

        redis_db.set("subscriber", subscriber_data)
        return response, []


def add_subscriber(command, channel):

    if command.__len__() >= 2:
        location = command[1]
        print "subscribing to {}".format(location)
        subscriber_data = None
        response = ""
        try:
            generate_24_hour_time_adzan(adzan_token, prayer, location)
            subscriber_data = ast.literal_eval(redis_db.get("subscriber"))
            print "subscriber {}".format(str(subscriber_data))
        except LookupError as le:
            response = le.message
            return response, []
        except Exception as e:
            print e.message
            print "read failed"

        if subscriber_data is None:
            subscriber_data = {location:[{}]}
        elif not location in subscriber_data:
            subscriber_data[location] = [{}]

        subscriber_location_data = subscriber_data[location][0]

        if channel in subscriber_location_data and subscriber_location_data[
            channel]=="active":
            response = "Already subscribed to {}".format(location)
        else:
            subscriber_location_data[channel] = "active"
            response = "Successfully subscribed to {}".format(location)
        subscriber_data[location][0] = subscriber_location_data

        redis_db.set("subscriber", subscriber_data)
        return response, []


def remove_subscriber(command, channel):

    if command.__len__() >= 2:
        location = command[1]
        print "removing subscription to {}".format(location)
        subscriber_data = None
        try:
            subscriber_data = ast.literal_eval(redis_db.get("subscriber"))
            print "subscriber {}".format(str(subscriber_data))
        except LookupError as le:
            response = le.message
            return response, []
        except Exception as e:
            print e.message
            print "read failed"

        if subscriber_data and location in subscriber_data and channel in \
                subscriber_data[location][0]:
            subscriber_location_data = subscriber_data[location][0]
            subscriber_location_data[channel] = "inactive"
            response = "Successfully unsubscribed to {}".format(location)
            subscriber_data[location][0] = subscriber_location_data
            redis_db.set("subscriber", subscriber_data)
        else:
            response = "User/Channel not subscribed to {}".format(location)
        return response, []


def get_subscriber():
    try:
        return ast.literal_eval(redis_db.get("subscriber")), []
    except:
        return "no subscriber data", []


def parse_command(command, channel):
    try: 
        if command[0] == 'adzan':
            location = 'yogyakarta'
            if command.__len__() > 2:
                location = command[2]
            return get_adzan_list(command[1], location)
        elif command[0] == 'subscribe':
            return add_subscriber(command,channel)
        elif command[0] == 'force_subscribe':
            return force_set_subscriber(command,channel)
        elif command[0] == 'unsubscribe':
            return remove_subscriber(command,channel)
        elif command[0] == 'list_subscriber':
            return get_subscriber()
        elif command[0] == 'today_ayah':
            return "ayah", get_random_ayah_attachment([])
    except Exception as e:
        print e.message


def get_adzan_list(prayer_day,location):
    return "Jadwal Sholat untuk wilayah {}".format(location), generate_24_hour_time_adzan(adzan_token, prayer,location,prayer_day)[1]

if __name__ == "__main__":
    response, attachment = parse_command(["today_ayah"], "")
    print response, attachment
