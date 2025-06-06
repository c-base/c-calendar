from convertcal import parse_ics, calendar_to_json


def test_recurrence_with_exception():
    ics = '''
BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
PRODID:-//SabreDAV//SabreDAV//EN
BEGIN:VEVENT
CREATED:20250605T182728Z
DTSTAMP:20250605T182810Z
LAST-MODIFIED:20250605T182810Z
SEQUENCE:3
UID:20a6265c-896c-4026-894b-73fb1108088b
DTSTART;VALUE=DATE:20250605
DTEND;VALUE=DATE:20250606
STATUS:CONFIRMED
SUMMARY:Repeating
RRULE:FREQ=WEEKLY;BYDAY=TH;COUNT=3
END:VEVENT
BEGIN:VEVENT
CREATED:20250605T182827Z
DTSTAMP:20250605T182827Z
LAST-MODIFIED:20250605T182827Z
SEQUENCE:1
UID:20a6265c-896c-4026-894b-73fb1108088b
DTSTART;VALUE=DATE:20250613
DTEND;VALUE=DATE:20250614
STATUS:CONFIRMED
SUMMARY:Repeating
DESCRIPTION:Exception that contains a description
RECURRENCE-ID;VALUE=DATE:20250612
END:VEVENT
END:VCALENDAR
'''

    calendar = parse_ics(ics)
    json_data = calendar_to_json(calendar, default_location='mainhall')

    assert len(json_data) == 3
    assert json_data[0]['description'] == ''
    assert json_data[1]['description'] == 'Exception that contains a description'
    assert json_data[1]['start'] == '2025-06-13'
