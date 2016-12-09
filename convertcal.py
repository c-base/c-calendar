#!/usr/bin/env python3
# coding: utf-8

"""convertcal.py: Converts several ICS files and exports a Javascript array suitable for fullcalendar.io."""

__author__      = "Ricardo Band <xen@c-base.org>, Uwe Kamper <uk@c-base.org>"
__copyright__   = "Copyright 2016, Berlin, Germany"

import urllib.request
from copy import copy
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime, timedelta
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
        de = event.get('dtend').dt
        location = event.get('location', default_location)
        description = event.get('description', '')
        is_all_day = False
        if not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day, tzinfo=pytz.utc)
            is_all_day = True

        if event.get('rrule'):
            event_template = {
                "id": ev_id,
                "title": event.get('summary'),
                "description": description,
                "location": location,
                "allDay": is_all_day
            }

            events = get_events_from_rrule(event, event_template, d, de)
            all_events.extend(events)
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


def get_events_from_rrule(ical_event, event_template, start_date, end_date):
    events = []

    ical_rrule = ical_event.get('rrule')
    ical_rrule_str = ical_rrule.to_ical().decode('utf-8')
    rrule = rrulestr(ical_rrule_str, ignoretz=True, dtstart=start_date.replace(tzinfo=None))
    ruleset = rruleset()
    ruleset.rrule(rrule)

    exdates = get_exdates(ical_event)
    for exdate in exdates:
        for exdate_date in exdate.dts:
            ruleset.exdate(exdate_date.dt.replace(tzinfo=None))

    after = datetime.utcnow() - timedelta(days=90)
    before = datetime.utcnow() + timedelta(days=365)
    rrule_instances = list(ruleset.between(after, before))
    for rrule_instance in rrule_instances:
        event = copy(event_template)
        event['start'] = rrule_instance.isoformat()

        if not event["allDay"]:
            instance_end_date = datetime(rrule_instance.year, rrule_instance.month, rrule_instance.day,
                                         end_date.hour, end_date.minute, end_date.second)
            event["end"] = instance_end_date.isoformat()

        events.append(event)

    return events


def get_exdates(ical_event):
    exdate_ical = ical_event.get('exdate')
    if not exdate_ical:
        exdates = []
    elif isinstance(exdate_ical, list):
        exdates = exdate_ical
    else:
        exdates = [exdate_ical]

    return exdates


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
