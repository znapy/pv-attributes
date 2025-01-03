"""Rules to determine date and time of last modify."""

from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from config import PERIODS, SYSTEM_ZONE
import helpers

YEARS = {year for period in PERIODS \
              for year in range(period.start.year, period.end.year + 1)}


def timezone_for_date(date_n_time: datetime, path: Path) -> ZoneInfo:
    """Get timezone for period."""
    for period in reversed(PERIODS):
        if not path.parent.is_relative_to(period.path):
            continue
        if period.start <= date_n_time.astimezone(SYSTEM_ZONE) \
                        <= period.end:
            return period.timezone
    return SYSTEM_ZONE

class FileStat(helpers.FileStatWithUTC):
    """File stat with system time zone."""
    @classmethod
    def system_zone(cls) -> ZoneInfo:
        """System zone from config."""
        return SYSTEM_ZONE


# return (True, date_n_time) if the rule is applied and new datetime is needed
RuleResult = tuple[bool, datetime | None]
Rule = Callable[[FileStat], RuleResult]

def appropriate(func: Rule, file_stat: FileStat) -> RuleResult:
    """
    Is the rule appropriate for the FileStat and the different datetime needed.
    """
    return func(file_stat)


def _get_date_n_time(candidate: str) -> datetime | None:
    """Get date and time from file part."""
    if len(candidate) != 15 \
            or candidate[:8].isdigit() is False \
            or candidate[8] != "_" \
            or candidate[9:15].isdigit() is False:
        return None

    try:
        return datetime.strptime(candidate, "%Y%m%d_%H%M%S")
    except ValueError:
        return None

def _apply_time_zone(date_n_time_stem: datetime, file_stat: FileStat
                     ) -> datetime | None:
    """Apply time zone for date and time."""
    if date_n_time_stem.year not in YEARS:
        print(f"Year {date_n_time_stem.year} for file '{file_stat.path}'"
              f" is not in years from periods.")
        return None

    timezone = timezone_for_date(date_n_time_stem, file_stat.path)
    date_n_time = date_n_time_stem.replace(tzinfo=timezone) \
                                  .astimezone(SYSTEM_ZONE)

    if date_n_time != file_stat.mtime:
        return date_n_time
    return None

def _first_digit_index(candidate: str) -> int | None:
    """Get index of first digit in candidate."""
    return next(
        (i for i, char in enumerate(candidate) if char.isdigit()),
        None)

def rule_date_n_time(file_stat: FileStat) -> RuleResult:
    """
    Date and time in name (may contain non-digit prefix).

    Examples:
        IMG_20191127_194031.jpg, IMG_20200201_205103_1.jpg,
        VID_20200801_081626_LS.mp4, PXL_20230906_111508295.jpg,
        PXL_20230906_122117759.TS.mp4, 20150617_191500.jpg
        PXL_20240102_112534347_exported_stabilized_1704194757966.gif
    """
    first_digit = _first_digit_index(file_stat.path.stem)
    if first_digit is None:
        return (False, None)

    date_n_time_stem = _get_date_n_time(
        file_stat.path.stem[first_digit:first_digit+15])
    if date_n_time_stem is None:
        return (False, None)

    return (True, _apply_time_zone(date_n_time_stem, file_stat))


def _get_date_without_time(candidate: str, date_format: str = "%Y%m%d"
                           ) -> datetime | None:
    """
    Get date and time from file part.

    The date_format may contains '%Y', '%m' and '%d'.
    """
    length = len(date_format.replace("%Y", "2020").replace("%m", "12")
                 .replace("%d", "31"))
    if len(candidate) < length:
        return None
    try:
        return datetime.strptime(candidate[:length], date_format)
    except ValueError:
        return None

def _add_time_from_stat(date_n_time_stem: datetime, file_stat: FileStat
                        ) -> datetime | None:
    """Add time to date from file mtime."""
    if date_n_time_stem.year not in YEARS:
        print(f"Year {date_n_time_stem.year} for file '{file_stat.path}'"
              f" is not in years from periods.")
        return None

    time = file_stat.mtime.astimezone(SYSTEM_ZONE).time()
    date_n_time = datetime.combine(date_n_time_stem.date(), time, SYSTEM_ZONE)

    if date_n_time != file_stat.mtime:
        return date_n_time
    return None

def rule_date_without_time(file_stat: FileStat) -> RuleResult:
    """
    Date without time in name.

    Example: 'VID-20200412-WA0000.mp4'.
    """
    first_digit = _first_digit_index(file_stat.path.stem)
    if first_digit is None:
        return (False, None)
    candidate = file_stat.path.stem[first_digit:]

    for date_format in ("%Y%m%d", "%Y-%m-%d"):
        date_in_name = _get_date_without_time(candidate, date_format)
        if date_in_name is None:
            continue
        return (True, _add_time_from_stat(date_in_name, file_stat))

    return (False, None)



def _parent_with_year(path: Path) -> Path | None:
    """Get parent directory started with year."""
    for parent in path.parents:
        year_part = parent.name[:4]
        if year_part.isdigit() and int(year_part) in YEARS:
            return parent
    return None

def rule_date_in_dir(file_stat: FileStat) -> RuleResult:
    """
    Date in directory name.

    Example: '/a/b/2020-12-31/SNC00001.jpg'.
    """
    if (parent := _parent_with_year(file_stat.path)) is None:
        return (False, None)

    for date_format in ("%Y-%m-%d", "%Y-%m", "%Y"):
        date_in_dir = _get_date_without_time(parent.name, date_format)
        if date_in_dir is None:
            continue

        date_n_time = date_in_dir.replace(tzinfo=SYSTEM_ZONE)
        if "%m" not in date_format:
            date_n_time = date_n_time.replace(month=file_stat.mtime.month)
        if "%d" not in date_format:
            date_n_time = date_n_time.replace(day=file_stat.mtime.day)
        return (True, _add_time_from_stat(date_n_time, file_stat))

    return (False, None)
