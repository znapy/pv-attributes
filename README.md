# About

Change in files the time of last modification (st_mtime file stat).
Different source directories can have different name patterns and time zones.

Some photo-video managers (f.e. [immich](https://immich.app/)) use the time modification from the file if there are no ExifTags inside the file. If you copied files without attributes preserve - these photos are not displayed correctly on the timeline. This script takes date from the file path/name and corrects the property.

# Requirements

- python3.12+
- POSIX system (tested on Ubuntu)

# Usage

Preparation:

1. Copy *config_example.py* to *config.py*
2. Change in *config.py* the *SYSTEM_ZONE* and *PERIODS* to your values (to get timezones list execute: `timedatectl list-timezones`).

Execute `python pva.py` (without parameter "-c" it displays the changes without changing the files).

To modify a time you should be a file owner (or root / sudo user).
