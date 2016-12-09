#!/usr/bin/env python3
# coding: utf-8

"""convertcal.py: Converts several ICS files and exports a Javascript array suitable for fullcalendar.io."""

__author__      = "Ricardo Band <xen@c-base.org, Uwe Kamper <uk@c-base.org>"
__copyright__   = "Copyright 2016, Berlin, Germany"

import urllib.request
import dateutil.rrule as rrule
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import json
import os

from icalendar import Calendar

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def do_one_ics(ics, default_location):
    events = []
    cal = Calendar.from_ical(ics)

    start = datetime.utcnow().replace(tzinfo=pytz.utc)
    end = start - relativedelta(years=1)

    all_events = []
    for ev_id, event in enumerate(cal.walk('vevent')):
        d = event.get('dtstart').dt
        de = get_end_date(event, d)
        if not de:
            print("Skipping event: %s" % event.get('summary'))
            continue

        location = event.get('location', default_location)
        description = event.get('description', '')
        is_all_day = False
        if not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day, tzinfo=pytz.utc)
            is_all_day = True
            
        r = event.get('rrule')
        if r:
            rstr = r.to_ical().decode('utf-8')
            rule = rrule.rrulestr(rstr, ignoretz=True, dtstart=d.replace(tzinfo=None))
            after = datetime.utcnow() - timedelta(days=90)
            before = datetime.utcnow() + timedelta(days=365)
            revents = list(rule.between(after, before))
            for ev in revents:
                current = {
                    "id": ev_id,
                    "title": event.get('summary'),
                    "start": ev.isoformat(),
                    "description": description,
                    "location": location
                }
                if is_all_day == True:
                    current["allDay"] = True
                else:
                    current["allDay"] = False
                    end_d = datetime(ev.year, ev.month, ev.day, de.hour, de.minute, de.second)
                    current["end"] = end_d.isoformat()
                all_events.append(current)
            continue

        current = {
            "id": ev_id,
            "title": event.get('summary'), 
            "start": d.isoformat(), 
            "description": description,
            "location": location
        }
        if is_all_day == True:
            current["allDay"] = True
            current["end"] = de.isoformat()
        else:
            current["allDay"] = False
            current["end"] = de.isoformat()
        all_events.append(current)

    return all_events


def get_end_date(event, start_date):
    dtend = event.get('dtend')
    if dtend:
        end_date = dtend.dt
    else:
        duration = event.get('duration')
        if not duration:
            return None
        end_date = start_date + duration.dt

    return end_date


export_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.js')
error_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'errors.js')

try:
    ics = urllib.request.urlopen('https://c.c-base.org/calendar/events.ics').read()
    c_base_events = do_one_ics(ics, 'mainhall')
    ics = urllib.request.urlopen('https://c.c-base.org/calendar/regulars.ics').read()
    regular_events = do_one_ics(ics, 'mainhall')
    url = "https://c.c-base.org/calendar/seminars.ics"
    ics = urllib.request.urlopen(url).read()
    seminar_events = do_one_ics(ics, "seminarraum")
except Exception as e:
    print(e)
    with open(os.path.realpath(error_name), mode="w") as outfh:
        outfh.write('window.c_base_errors = ' + json.dumps(str(e)) + ";\n")
    exit(1)

with open(os.path.realpath(export_name), mode="w") as outfh:
    outfh.write("window.c_base_regulars = " + json.dumps(regular_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.c_base_events = " + json.dumps(c_base_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.c_base_seminars= " + json.dumps(seminar_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.lastUpdate = \"" + datetime.now().isoformat() +"\";\n")

with open(os.path.realpath(error_name), mode="w") as outfh:
    outfh.write('window.c_base_errors = "";\n')

exit(0)
