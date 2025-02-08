from typing import Tuple
import datetime as dt

def get_last_month_and_year(current_year:str, current_month: int) -> Tuple[int, int]:
        last_month = 12 if current_month == 1 else current_month - 1
        last_year = current_year if current_month != 1 else current_year - 1
        return (last_month, last_year)

def get_last_month_and_year_from_datetime(current_datetime: dt.datetime) -> Tuple[int, int]:
        return get_last_month_and_year(current_year=current_datetime.year, current_month=current_datetime.month)