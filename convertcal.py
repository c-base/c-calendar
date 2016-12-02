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

def do_one_ics(ics):
    events = []
    cal = Calendar.from_ical(ics)

    start = datetime.utcnow().replace(tzinfo=pytz.utc)
    end = start - relativedelta(years=1)

    all_events = []
    for ev_id, event in enumerate(cal.walk('vevent')):
        d = event.get('dtstart').dt
        de = event.get('dtend').dt
        is_all_day = False
        if not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day, tzinfo=pytz.utc)
            is_all_day = True
        print(d.strftime(DATE_FORMAT), ':', de.strftime(DATE_FORMAT))
        print(event.get('summary'))
            
        r = event.get('rrule')
        if r:
            rstr = r.to_ical().decode('utf-8')
            print("RSTR", rstr)
            rule = rrule.rrulestr(rstr, ignoretz=True, dtstart=d.replace(tzinfo=None))
            after = datetime.utcnow() - timedelta(days=90)
            before = datetime.utcnow() + timedelta(days=365)
            revents = list(rule.between(after, before))
            for ev in revents:
                current = {
                    "id": ev_id,
                    "title": event.get('summary'),
                    "start": ev.isoformat(),
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
        }
        if is_all_day == True:
            current["allDay"] = True
        else:
            current["allDay"] = False
            current["end"] = de.isoformat()
        all_events.append(current)

    return all_events


export_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.js')

with open(os.path.realpath(export_name), mode="w") as outfh:
    ics = urllib.request.urlopen('https://c.c-base.org/calendar/events.ics').read()
    all_events = do_one_ics(ics)
    outfh.write("window.c_base_events = " + json.dumps(all_events, indent=4, sort_keys=True) + ";\n")
    ics = urllib.request.urlopen('https://c.c-base.org/calendar/regulars.ics').read()
    all_events = do_one_ics(ics)
    outfh.write("window.c_base_regulars = " + json.dumps(all_events, indent=4, sort_keys=True) + ";\n")
    url = "https://c.c-base.org/calendar/seminars.ics"
    ics = urllib.request.urlopen(url).read()
    all_events = do_one_ics(ics)
    outfh.write("window.c_base_seminars= " + json.dumps(all_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.stand = \"" + datetime.now().isoformat() +"\";\n")
