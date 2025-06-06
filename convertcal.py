#!/usr/bin/env python3
# coding: utf-8

"""convertcal.py: Converts several ICS files and exports a Javascript array suitable for fullcalendar.io."""

__author__ = "Ricardo Band <xen@c-base.org>, Uwe Kamper <uk@c-base.org>, cketti <cketti@c-base.org>"
__copyright__ = "Copyright 2016-2025, Berlin, Germany"

import urllib.request
from copy import copy
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime, timedelta, date
import pytz
import json
import os
import re
import sys
import traceback

from icalendar import Calendar

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Parameter dict used for timedeltas, e.g. timedelta(**INTO_PAST)
# From now, what is the oldest date that we want to list?
INTO_PAST = {
    'days': 365
}

berlin = pytz.timezone('Europe/Berlin')

# Parameter dict used for timedeltas, e.g. timedelta(**INTO_FUTURE)
# From now, what is the furthest we want to expand recurring events into the future.
INTO_FUTURE = {
    'days': 365
}


class EventContainer:
    """
    Container for an `icalendar.cal.Event` and its associated exception event entries.
    """

    def __init__(self):
        self.main_event = None
        self.overrides = {}


def calendar_to_json(ics, default_location):
    """
    Convert iCalendar data to a dictionary that can be used to generate the data for fullcalendar.io.
    """

    grouped_events = group_events(ics)
    return events_to_fullcalendar_json(grouped_events, default_location)


def group_events(calendar):
    """
    Associate recurring events in a calendar with their exception entries.
    """

    event_containers = {}
    for event in calendar.walk('vevent'):
        uid = str(event.get('uid'))

        try:
            container = event_containers[uid]
        except KeyError:
            container = EventContainer()
            event_containers[uid] = container

        if event.get('recurrence-id'):
            date_key = to_date_string(event.get('recurrence-id').dt)
            container.overrides[date_key] = event
        else:
            container.main_event = event

    return list(event_containers.values())


def events_to_fullcalendar_json(event_containers, default_location):
    json_events = []
    past_cutoff_date = datetime.now().astimezone(berlin) - timedelta(**INTO_PAST)

    for json_index, event_container in enumerate(event_containers):
        event = event_container.main_event
        date_start = to_datetime(event, 'dtstart')

        # If the event is a recurring event
        if event.get('rrule'):
            event_template = event_to_json(event, json_index, default_location)
            del event_template['start']
            try:
                del event_template['end']
            except KeyError:
                pass

            date_end = get_end_date(event, date_start)
            jsons = build_json_events_from_rrule(event_container, event_template, date_start, date_end)

            json_events.extend(jsons)
            continue

        # Ignore events that are older than the specified cut-off date.
        if date_start < past_cutoff_date:
            continue

        # This is a non-recurring event. Use it as-is.
        current = event_to_json(event, json_index, default_location)
        json_events.append(current)

    return json_events


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


def build_json_events_from_rrule(event_container, event_template, start_date, end_date):
    json_events = []

    event = event_container.main_event
    ical_rrule = event.get('rrule')
    ical_rrule_str = ical_rrule.to_ical().decode('utf-8')
    rrule = rrulestr(ical_rrule_str, ignoretz=True, dtstart=start_date.replace(tzinfo=None))
    ruleset = rruleset()
    ruleset.rrule(rrule)

    exclusion_dates = get_exclusion_dates(event)
    for exclusion_date in exclusion_dates:
        for exclusion_date_date in exclusion_date.dts:
            datetime_or_date = exclusion_date_date.dt
            if isinstance(datetime_or_date, datetime):
                exclusion_datetime = datetime_or_date.replace(tzinfo=None)
            elif isinstance(datetime_or_date, date):
                exclusion_datetime = datetime(
                    year=datetime_or_date.year,
                    month=datetime_or_date.month,
                    day=datetime_or_date.day)
            else:
                continue

            ruleset.exdate(exclusion_datetime)

    after = datetime.now() - timedelta(**INTO_PAST)
    before = datetime.now() + timedelta(**INTO_FUTURE)
    rrule_instances = list(ruleset.between(after, before))
    for index, occurrence_datetime in enumerate(rrule_instances, start=1):
        date_key = to_date_string(occurrence_datetime)
        try:
            override_event = event_container.overrides[date_key]
            event = event_to_json(override_event, event_template['id'], event_template['location'])
        except KeyError:
            event = copy(event_template)
            if event['allDay']:
                event['start'] = occurrence_datetime.date().isoformat()
            else:
                event['start'] = occurrence_datetime.replace(tzinfo=end_date.tzinfo).isoformat()
                event['end'] = datetime(
                    year=occurrence_datetime.year,
                    month=occurrence_datetime.month,
                    day=occurrence_datetime.day,
                    hour=end_date.hour,
                    minute=end_date.minute,
                    second=end_date.second,
                    tzinfo=end_date.tzinfo,
                ).isoformat()

        event['uid'] = '{}-{}'.format(event_template['uid'], index)

        json_events.append(event)

    return json_events


def get_exclusion_dates(ical_event):
    exdate = ical_event.get('exdate')
    if not exdate:
        exclusion_dates = []
    elif isinstance(exdate, list):
        exclusion_dates = exdate
    else:
        exclusion_dates = [exdate]

    return exclusion_dates


def event_to_json(event, json_id, default_location):
    date_start = event.get('dtstart').dt

    is_all_day = False
    if not isinstance(date_start, datetime):
        is_all_day = True

    json_data = {
        'id': json_id,
        'uid': str(event.get('uid')),
        'title': clean_up_title(event.get('summary')),
        'description': event.get('description', ''),
        'location': event.get('location', default_location),
        'allDay': is_all_day,
        'start': date_start.isoformat(),
    }

    if not is_all_day:
        json_data['end'] = get_end_date(event, date_start).isoformat()

    return json_data


def clean_up_title(title):
    if title is None:
        return 'Kein Titel'

    return re.sub(r'\n', ' ', title)


def to_date_string(datetime_or_date):
    return datetime_or_date.strftime('%Y-%m-%d')


def to_datetime(ical_event, field):
    date_value = ical_event.get(field).dt
    if isinstance(date_value, datetime):
        return date_value
    else:
        return datetime(date_value.year, date_value.month, date_value.day).astimezone(berlin)


def merge_calendars(calendars):
    merged_calendar = Calendar()
    merged_calendar.add('prodid', '-//' + 'c-base' + '//' + 'c-base.org' + '//')
    merged_calendar.add('version', '2.0')
    merged_calendar.add('x-wr-calname', 'c-base events')

    for calendar in calendars:
        for event in calendar.walk('vevent'):
            merged_calendar.add_component(event)

    return merged_calendar


def download_and_parse_ics(url):
    ics = urllib.request.urlopen(url).read()
    return parse_ics(ics)


def parse_ics(ics):
    return Calendar.from_ical(ics)


def main():
    export_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.js')
    export_json_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.json')
    merged_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'c-base-events.ics')
    error_name = os.path.join(os.path.dirname(__file__), 'html', 'exported', 'errors.js')

    try:
        events_calendar = download_and_parse_ics('https://c.c-base.org/calendar/events.ics')
        c_base_events = calendar_to_json(events_calendar, default_location='mainhall')

        regulars_calendar = download_and_parse_ics('https://c.c-base.org/calendar/regulars.ics')
        regular_events = calendar_to_json(regulars_calendar, default_location='mainhall')

        online_calendar = download_and_parse_ics('https://c.c-base.org/calendar/online.ics')
        online_events = calendar_to_json(online_calendar, default_location='https://jitsi.c-base.org/mainhall')

        seminars_calendar = download_and_parse_ics('https://c.c-base.org/calendar/seminars.ics')
        seminar_events = calendar_to_json(seminars_calendar, default_location='seminarraum')

        # No errors happened. Make it known to the world!
        with open(os.path.realpath(error_name), mode='w') as outfh:
            outfh.write('window.c_base_errors = "";\n')
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print('### ERROR : ', str(e))

        with open(os.path.realpath(error_name), mode='w') as outfh:
            outfh.write('window.c_base_errors = ' + json.dumps(str(e)) + ';\n')

        exit(1)

    with open(os.path.realpath(export_name), mode='w') as outfh:
        outfh.write('window.c_base_regulars = ' + json.dumps(regular_events, indent=4, sort_keys=True) + ';\n')
        outfh.write('window.c_base_events = ' + json.dumps(c_base_events, indent=4, sort_keys=True) + ';\n')
        outfh.write('window.c_base_seminars= ' + json.dumps(seminar_events, indent=4, sort_keys=True) + ';\n')
        outfh.write('window.c_base_online = ' + json.dumps(online_events, indent=4, sort_keys=True) + ';\n')
        outfh.write('window.lastUpdate = "' + datetime.now().isoformat() + ' UTC";\n')

    all_events = {
        'c_base_regulars': regular_events,
        'c_base_events': c_base_events,
        'c_base_seminars': seminar_events,
        'c_base_online': online_events,
        'lastUpdate': datetime.now().isoformat() + ' UTC'
    }

    with open(os.path.realpath(export_json_name), mode='w') as outfh:
        outfh.write(json.dumps(all_events, indent=4, sort_keys=True) + '\n')

    with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'events.ics'), 'wb') as f:
        f.write(events_calendar.to_ical())

    with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'regulars.ics'), 'wb') as f:
        f.write(regulars_calendar.to_ical())

    with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'seminars.ics'), 'wb') as f:
        f.write(seminars_calendar.to_ical())

    with open(os.path.join(os.path.dirname(__file__), 'html', 'exported', 'online.ics'), 'wb') as f:
        f.write(online_calendar.to_ical())

    merged_calendar = merge_calendars([events_calendar, regulars_calendar, online_calendar, seminars_calendar])
    with open(os.path.realpath(merged_name), 'wb') as f:
        f.write(merged_calendar.to_ical())
        f.close()

    with open(os.path.realpath(error_name), mode='w') as outfh:
        outfh.write('window.c_base_errors = "None";\n')


if __name__ == '__main__':
    main()
    exit(0)
