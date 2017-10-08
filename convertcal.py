#!/usr/bin/env python3
# coding: utf-8

"""convertcal.py: Converts several ICS files and exports a Javascript array suitable for fullcalendar.io."""

__author__      = "Ricardo Band <xen@c-base.org>, Uwe Kamper <uk@c-base.org>, Cketti <cketti@c-base.org>"
__copyright__   = "Copyright 2016-2017, Berlin, Germany"

import urllib.request
from copy import copy
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import json
import os
import re

from icalendar import Calendar

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Parameter dict used for timedeltas, e.g. timedelta(**INTO_PAST)
# From now, what is the oldest date that we want to list?
INTO_PAST = {
    'days': 365
}

# Parameter dict used for timedeltas, e.g. timedelta(**INTO_FUTURE)
# From now, what is the furthest we want to expand recurring events into the future.
INTO_FUTURE = {
    'days': 365
}

newcal = Calendar()
newcal.add('prodid', '-//' + 'c-base' + '//' + 'c-base.org' + '//')
newcal.add('version', '2.0')
newcal.add('x-wr-calname', 'c-base events')

def do_one_ics(ics, default_location):
    events = []
    global newcal
    cal = Calendar.from_ical(ics)
    oldest_non_recurring = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(**INTO_PAST)
    
    all_events = []
    for ev_id, event in enumerate(cal.walk('vevent')):
        newcal.add_component(event)
        d = event.get('dtstart').dt
        de = get_end_date(event, d)
        title = clean_up_title(event.get('summary'))
        if not de:
            print("Skipping event: %s" % title)
            continue

        location = event.get('location', default_location)
        description = event.get('description', '')
        is_all_day = False
        if not isinstance(d, datetime):
            d = datetime(d.year, d.month, d.day, tzinfo=pytz.utc)
            is_all_day = True

        # If the event is a recurring event
        if event.get('rrule'):
            event_template = {
                "id": ev_id,
                "title": title,
                "description": description,
                "location": location,
                "allDay": is_all_day
            }

            events = get_events_from_rrule(event, event_template, d, de)
            all_events.extend(events)
            continue
        
        # Ignore regular events that are older than one year.
        if d < oldest_non_recurring:
            print("Skipping non-recurring event %s because it is too old (%s)" %(event.get('summary'), d.isoformat()))
        
        # This is just a regular event, just use it as is
        current = {
            "id": ev_id,
            "title": title,
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
    # import pudb; pu.db
    return all_events


def clean_up_title(title):
    return re.sub(r"\n", " ", title)


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

    after = datetime.utcnow() - timedelta(**INTO_PAST)
    before = datetime.utcnow() + timedelta(**INTO_FUTURE)
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
merged_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'c-base-events.ics')
error_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'errors.js')

try:
    events_ics = urllib.request.urlopen('https://c.c-base.org/calendar/events.ics').read()
    c_base_events = do_one_ics(events_ics, 'mainhall')
    regulars_ics = urllib.request.urlopen('https://c.c-base.org/calendar/regulars.ics').read()
    regular_events = do_one_ics(regulars_ics, 'mainhall')
    url = "https://c.c-base.org/calendar/seminars.ics"
    seminars_ics = urllib.request.urlopen(url).read()
    seminar_events = do_one_ics(seminars_ics, "seminarraum")
except Exception as e:
    print(e)
    with open(os.path.realpath(error_name), mode="w") as outfh:
        outfh.write('window.c_base_errors = ' + json.dumps(str(e)) + ";\n")
    exit(1)

with open(os.path.realpath(export_name), mode="w") as outfh:
    outfh.write("window.c_base_regulars = " + json.dumps(regular_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.c_base_events = " + json.dumps(c_base_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.c_base_seminars= " + json.dumps(seminar_events, indent=4, sort_keys=True) + ";\n")
    outfh.write("window.lastUpdate = \"" + datetime.now().isoformat() +" UTC\";\n")

with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.ics'), 'wb') as f:
    f.write(events_ics)

with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'regulars.ics'), 'wb') as f:
    f.write(regulars_ics)

with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'seminars.ics'), 'wb') as f:
    f.write(seminars_ics)

with open(os.path.realpath(merged_name) , 'wb') as f:
    f.write(newcal.to_ical())
    f.close()

with open(os.path.realpath(error_name), mode="w") as outfh:
    outfh.write('window.c_base_errors = "None";\n')

exit(0)
