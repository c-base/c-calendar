# c-calendar - a calendar for www.c-base.org

This script converts multiple ICS feeds into a JSON/Javascript format that can be
understood by fullcalendar.io. The calendar is then displayed on c-base.org

## How to install (in production)

Check out the repo to `/opt/c-calendar`

```
cd /opt/c-calendar
uv sync --no-dev
```

Then you can run `/opt/c-calendar/run_convert.sh` from anywhere (e.g. a cronjob)


## How to setup for development

Run the following commands on your dev machine:

```
git clone https://github.com/uwekamper/c-calendar.git
cd c-calendar
uv sync 
```

During development:

- Running the script: `uv run pytest`
- Running the script: `uv run convertcal.py`

