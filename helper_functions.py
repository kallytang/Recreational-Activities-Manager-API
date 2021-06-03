import time
import calendar
import datetime
from constants import *
from google.cloud import datastore

client = datastore.Client()


# check if date
def validate_date(start, end):
    if start < CONST_START_DATE_CUTOFF or end < CONST_START_DATE_CUTOFF:
        return False
    if start > end:
        return False
    return True


# def check_overlap(start, end, room):


def validate_activity_name(name: str):
    name_string = name.replace(" ", "")
    name_string = name_string.replace("-", "")
    name_string = name_string.replace("-", "")
    if name_string:
        for letter in name_string:
            if not letter.isalpha() and not letter.isdigit():
                return False

    return True


def validate_length(min_len, max_len, desc):
    if desc is None:
        return False
    if len(desc) < min_len or len(desc) > max_len:
        return False

    return True


def room_available(room, start_time, end_time):
    query = client.query(kind=ACTIVITIES)
    query.add_filter("room", "=", room)

    result = list(query.fetch())

    for item in result:

        if item[START] == start_time and item[END] == end_time:
            return False
        # if start time overlaps with the interval
        if end_time > item[START] > start_time:
            return False
        # if the end time overlaps with interval
        if end_time > item[END] > start_time:
            return False
        # if the passed item is within the interval of an existing class
        if item[START] < start_time and item[END] > end_time:
            return False
        # if the passed item overlaps inside the item
        if item[START] > start_time and item[END] < end_time:
            return False

    return True
