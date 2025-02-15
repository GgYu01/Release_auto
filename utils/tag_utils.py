import datetime

def parse_version_identifier(version_identifier):
    try:
        parts = version_identifier.split('_')
        if len(parts) != 3:
            return None
        year = int(parts[0])
        month_day = parts[1]
        day_counter = int(parts[2])

        month = int(month_day[0:2])
        day = int(month_day[2:4])

        tag_date = datetime.datetime(year, month, day).date()
        return {"date": tag_date, "counter": day_counter}
    except ValueError:
        return None

def generate_next_version_identifier(parsed_version_data, current_time):
    tag_date = parsed_version_data["date"]
    day_counter = parsed_version_data["counter"]
    current_date = current_time.date()

    if current_date > tag_date:
        return current_time.strftime("%Y_%m%d_01")
    elif current_date == tag_date:
        next_counter = day_counter + 1
        return current_time.strftime(f"%Y_%m%d_{next_counter:02d}")
    else:
        return None
