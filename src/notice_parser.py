import datetime
import logging
import os
import re
from enum import StrEnum

MONTH_LOOKUP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

DATE_REGEX = re.compile(r"^ ?(?:[A-z]+,? )?([0-9]+)[A-z]* ([A-z]+)(?: ([0-9]+))?")

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

LOGGER = logging.getLogger(__name__)


class NoticeParseError(Exception):
    """Raised when a notice does not match a supported proclamation format."""


class Territory(StrEnum):
    ENGLAND_AND_WALES = "England and Wales"
    SCOTLAND = "Scotland"
    NORTHERN_IRELAND = "Northern Ireland"


type HolidaysByTerritory = dict[Territory, set[datetime.date]]


def parse_date(string: str) -> tuple[str, datetime.date]:
    """
    Parse a date in the format used in proclamations - something like "monday, 28th december 2015"
    """
    LOGGER.debug("Parsing date '%s'", string)
    res = DATE_REGEX.search(string)
    if res is None:
        LOGGER.debug("Failed to match date '%s', this is probably fine", string)
        raise NoticeParseError("Failed to match date")
    LOGGER.debug("Date parse regex result '%s'", str(res.groups()))

    # Remove the part of the string that matched the regex
    string = string[len(res[0]) :]

    # Create a date object from the regex capture groups
    # Sometimes the year isn't present so we'll set it to the minimum year and update it later
    day = int(res[1])
    month = MONTH_LOOKUP[res[2]]
    if len(res.groups()) >= 3 and res[3]:
        year = int(res[3])
    else:
        LOGGER.debug("Year not present in '%s'", res[0])
        year = datetime.MINYEAR
    date = datetime.date(year, month, day)

    return (string, date)


def parse_date_list(
    string: str, next_is_negative: bool = False
) -> tuple[str, list[datetime.date], list[datetime.date]]:
    """
    Parse a list of dates, e.g. "tuesday 27th december 2016 and monday 29th may 2017" or "thursday 2nd june 2022 in place of monday 30th may 2022 and friday 3rd june 2022"
    """
    LOGGER.debug("Parsing date list '%s'", string)
    dates = []
    neg_dates = []
    yearless_dates = []
    while True:
        try:
            string, date = parse_date(string)
        except NoticeParseError as error:
            # This wasn't a date - stop trying to parse any more
            LOGGER.debug("Failed to parse date - assuming not a date '%s'", error)
            break

        # Add date to appropriate list and reset negative flag
        if date.year == datetime.MINYEAR:
            # No year found, update it later
            yearless_dates.append((next_is_negative, date))
        else:
            # A year was found, this means that the yearless dates can be updated
            for negative, yrldate in yearless_dates:
                (neg_dates if negative else dates).append(
                    datetime.date(date.year, yrldate.month, yrldate.day)
                )
            yearless_dates.clear()
            # And add the parsed date itself
            (neg_dates if next_is_negative else dates).append(date)
        next_is_negative = False

        string = string.removeprefix(",")

        # Sometimes the text afterwards signifies the next date will *not* be a bank holiday
        if string.startswith(" in the place of "):
            string = string[len(" in the place of ") :]
            next_is_negative = True
        elif string.startswith(" in place of "):
            string = string[len(" in place of ") :]
            next_is_negative = True
        elif string.startswith(" instead of "):
            string = string[len(" instead of ") :]
            next_is_negative = True
        elif string.startswith(" and appointing "):
            string = string[len(" and appointing ") :]
        elif string.startswith(" appointing "):
            string = string[len(" appointing ") :]
        elif string.startswith(" and "):
            string = string[len(" and ") :]
    return (string, dates, neg_dates)


def parse_territories(string: str) -> tuple[str, set[Territory]]:
    territories = set()
    remainder = string

    while True:
        territory_match = next(
            (
                (name, territory)
                for name, territory in (
                    ("northern ireland", Territory.NORTHERN_IRELAND),
                    ("england", Territory.ENGLAND_AND_WALES),
                    ("wales", Territory.ENGLAND_AND_WALES),
                    ("scotland", Territory.SCOTLAND),
                )
                if remainder.startswith(name)
                and (len(remainder) == len(name) or not remainder[len(name)].isalpha())
            ),
            None,
        )
        if territory_match is None:
            if territories:
                break
            raise NoticeParseError("Missing or unsupported territory")

        name, territory = territory_match
        remainder = remainder[len(name) :]
        territories.add(territory)

        separator = next(
            (
                separator
                for separator in (", and ", ", ", " and ")
                if remainder.startswith(separator)
            ),
            None,
        )
        if separator is None:
            break

        next_territory = remainder[len(separator) :]
        if next_territory.startswith("appointing "):
            break
        if not any(
            next_territory.startswith(name)
            and (
                len(next_territory) == len(name)
                or not next_territory[len(name)].isalpha()
            )
            for name, _ in (
                ("northern ireland", Territory.NORTHERN_IRELAND),
                ("england", Territory.ENGLAND_AND_WALES),
                ("wales", Territory.ENGLAND_AND_WALES),
                ("scotland", Territory.SCOTLAND),
            )
        ):
            raise NoticeParseError("Missing or unsupported territory")
        remainder = next_territory

    return remainder, territories


def add_dates_by_territory(
    result: HolidaysByTerritory,
    territories: set[Territory],
    dates: list[datetime.date],
) -> None:
    if not dates:
        return
    for territory in territories:
        result.setdefault(territory, set()).update(dates)


def parse_proclamation(
    string: str,
) -> tuple[HolidaysByTerritory, HolidaysByTerritory]:
    bh_dates: HolidaysByTerritory = {}
    neg_dates: HolidaysByTerritory = {}
    next_is_negative = False
    previous_territories: set[Territory] | None = None
    while True:
        string, new_dates, new_neg_dates = parse_date_list(string, next_is_negative)
        LOGGER.debug("Parsed dates '%s', '%s' for country", new_dates, new_neg_dates)

        string = string.removeprefix(",")

        # We should now have a part which declares the dates will be bank holidays in a list of countries
        # This is only the case though if this was not an "in place of", or it was but further appointed days followed
        if (not (next_is_negative or len(neg_dates) > 0)) or len(new_dates) > 0:
            if string.startswith(" a bank holiday in "):
                string = string[len(" a bank holiday in ") :]
            elif string.startswith(" as bank holidays in "):
                string = string[len(" as bank holidays in ") :]
            elif string.startswith(" as a bank holiday in "):
                string = string[len(" as a bank holiday in ") :]
            elif string.startswith(" as a bank and public holiday in "):
                string = string[len(" as a bank and public holiday in ") :]
            elif string.startswith(" as a bank and public and public holiday in "):
                # lol
                string = string[len(" as a bank and public and public holiday in ") :]
            else:
                LOGGER.error("Unexpected text within proclamation '%s'", string)
                raise NoticeParseError("Unexpected text within proclamation")
            string, previous_territories = parse_territories(string)
            add_dates_by_territory(bh_dates, previous_territories, new_dates)
            add_dates_by_territory(neg_dates, previous_territories, new_neg_dates)
        elif next_is_negative:
            if previous_territories is None:
                raise NoticeParseError("Negative dates have no territory")
            add_dates_by_territory(neg_dates, previous_territories, new_neg_dates)

        string = string.removeprefix(",")

        next_is_negative = False
        # There may be another list of dates for a different country
        if string.startswith(" and appointing "):
            string = string[len(" and appointing ") :]
        elif string.startswith(" appointing "):
            string = string[len(" appointing ") :]
        elif string.startswith(" in the place of "):
            string = string[len(" in the place of ") :]
            next_is_negative = True
        elif string.startswith(" in place of "):
            string = string[len(" in place of ") :]
            next_is_negative = True
        elif string.startswith(" instead of "):
            string = string[len(" instead of ") :]
            next_is_negative = True
        else:
            break

    string = string.removeprefix(".")

    string = string.removeprefix(" elizabeth r ")

    string = string.removeprefix(" elizabeth r")

    string = string.removeprefix(".")

    # Who decided to add this...
    if string.startswith(" the proclamation of a bank holiday directly "):
        string = ""

    if string:
        LOGGER.error("Unexpectedd extra text in proclamation '%s'", string)
        raise NoticeParseError("Unexpected extra text in proclamation")

    return (bh_dates, neg_dates)


def parse_notice(string: str) -> tuple[HolidaysByTerritory, HolidaysByTerritory]:
    """
    Parse a bank holiday proclamation notice and return the dates made bank holidays, and the dates made no longer bank holidays
    """
    LOGGER.debug("Parsing notice '%s'", string)
    string = string.lower()
    # Remove everything from the "Whereas" / "Now, therefore" - we only want the title which precedes it.
    string = string.split("whereas", 1)[0]
    string = string.split("now, therefore", 1)[0]
    string = string.replace("king", "queen").replace(
        "charles r", "elizabeth r"
    )  # Makes it easier to parse if we can assume queen
    string = string.replace("p roclamation", "proclamation")  # line replacement issues
    string = string.strip()
    LOGGER.debug("Cleant up notice: '%s'", string)

    # Different preambles to a proclamation
    if string.startswith("by the queen a proclamation appointing "):
        string = string[len("by the queen a proclamation appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif string.startswith("a proclamation appointing "):
        string = string[len("a proclamation appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif string.startswith("proclamation by the queen a proclamation appointing "):
        string = string[len("proclamation by the queen a proclamation appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif string.startswith("appointing "):
        string = string[len("appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif string.startswith("by the queen a proclamation elizabeth r. appointing "):
        string = string[len("by the queen a proclamation elizabeth r. appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif (
        "proclamation by the secretary of state" in string
        or "financial dealings act 1971" in string
    ) and "order appointing " in string:
        string = string[string.find("order appointing ") + len("order appointing ") :]
        bhs, nbhs = parse_proclamation(string)
        return (bhs, nbhs)
    elif (
        "lord high chancellor of great britain" in string
        and "great seal of the realm" in string
    ):
        # Notice accompanying some bank holiday notices asking them to be affixed with the great seal
        LOGGER.warning("Skipping notice relating to great seal")
        return ({}, {})

    LOGGER.error(
        "Couldn't parse notice as it did not match any expected format: '%s'", string
    )
    raise NoticeParseError(
        "Couldn't parse notice as it did not match any expected format"
    )
