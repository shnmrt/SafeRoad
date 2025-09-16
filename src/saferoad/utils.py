import re
import time
from datetime import datetime
from dateutil import parser as dsparser


def extract_dates(column_names: list[str]) -> tuple[list[str], list[datetime]]:
    """Extracts date fields from a list of column names.

    :param column_names: List of column names to search for dates.
    :type column_names: list[str]
    :return: A tuple containing two numpy arrays: one with the column names and another with the parsed date objects.
    :rtype: tuple[ndarray, ndarray]
    """
    assert isinstance(column_names, list), "column_names must be a list of strings"
    assert all(
        isinstance(name, str) for name in column_names
    ), "All items in column_names must be strings"
    assert len(column_names) > 0, "column_names must not be empty"

    nameFields: list = []
    dateFields: list = []
    for date in column_names:
        dateSearch = re.search(r"\d{8}", date)
        if dateSearch:
            pdate: datetime = dsparser.parse(dateSearch.group(), fuzzy=True).date()
            dateFields.append(pdate)
            nameFields.append(date)
    return nameFields, dateFields


def time_vector(dates: list[datetime]) -> list[float]:
    """Generates a time vector in days from a list of datetime objects.

    :param dates: List of datetime objects.
    :type dates: list[datetime]
    :return: List of time differences in days from the first date.
    :rtype: list[float]
    """
    return [(i - dates[0]).days for i in dates]


class Timer(object):
    """Context manager for timing code execution."""

    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        if self.name:
            print("%s took %.2f seconds" % (self.name, time.time() - self.tstart))
