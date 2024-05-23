from zoneinfo import ZoneInfo

def change_timezone(from_dt, from_timezone, to_timezone):
    from_dt = from_dt.replace(tzinfo=ZoneInfo(from_timezone))
    to_dt = from_dt.astimezone(ZoneInfo(to_timezone))
    return to_dt