import datetime
import re


def convert_time_to24(time12: str) -> str:
    """
    takes 'hh:MM:SS AM' or 'hh:MM:SS PM' and returns
    'HH:MM:SS' in 24-hour format.
    convertTimeTo24('12:XX:XX AM') will return 00:XX:XX
    convertTimeTo24('12:XX:XX AM') will return 12:XX:XX
    """
    if time12[-2:] == "AM" and time12[:2] == "12":
        return "00" + time12[2:-2]
    elif time12[-2:] == "AM":
        return time12[:-2]
    elif time12[-2:] == "PM" and time12[:2] == "12":
        return time12[:-2]
    else:
        return str(int(time12[:2]) + 12) + time12[2:8]


def separate_day_month_year(today_date: str) -> tuple:
    if not check_if_date_valid(today_date):
        raise ValueError("Wrong date format is passed!")
    year, month, day = [int(m) for m in today_date.split("-")]
    day = min(day, number_of_days_in_month(month, year))
    return day, month, year


def parse_date(date_val):
    if date_val is None:
        return str(datetime.date.today())
    else:
        if not check_if_date_valid(date_val):
            raise ValueError("date format not valid, should be YYYY-MM-DD")
        return date_val


def get_months_beginning(month: int, year: int) -> datetime:
    return datetime.datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d')


def get_months_end(month: int, year: int) -> datetime:
    return get_next_months_beginning(month, year) - datetime.timedelta(days=1)


def get_next_day(current_day: str) -> str:
    return str((datetime.datetime.strptime(current_day, '%Y-%m-%d') + datetime.timedelta(days=1)).date())


def get_next_months_beginning(month: int, year: int) -> datetime:
    if month < 12:
        return datetime.datetime.strptime(f"{year}-{month+1}-01", '%Y-%m-%d')
    else:
        return datetime.datetime.strptime(f"{year+1}-01-01", '%Y-%m-%d')


def get_thirty_days_from_now(day: int, month: int, year: int) -> datetime:
    """
    returns a datetime object, thirty days in future of the input value
    """
    if month < 12:
        return datetime.datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')+datetime.timedelta(days=30)
    else:
        return datetime.datetime.strptime(f"{year+1}-{month}-{day}", '%Y-%m-%d')


def number_of_days_in_month(month: int, year: int) -> int:
    return int(get_months_end(month, year).day)


def check_if_date_valid(date: str) -> bool:
    """
    check format of the date
    """
    check_format = re.compile(r'\d\d\d\d-\d\d-\d\d')
    if check_format.match(date) is None:
        return False
    return True
