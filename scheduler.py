#!/usr/bin/env python3

import os
import sys
import json
import time
from datetime import datetime
from lib.utils import logger
from run import main as run_main


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_current_time_window(sleep_schedule):
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    current_time_minutes = current_hour * 60 + current_minute

    for window in sleep_schedule:
        start_hour, start_minute = window["start"]
        end_hour, end_minute = window["end"]

        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute

        if start_minutes > end_minutes:
            if current_time_minutes >= start_minutes or current_time_minutes < end_minutes:
                return window["sleep"]
        else:
            if start_minutes <= current_time_minutes < end_minutes:
                return window["sleep"]

    logger.console_error("No matching time window found, using default 300s")
    return 300


def run_monitor():
    try:
        run_main()
        return True
    except Exception as e:
        logger.console_error(f"Monitor execution failed: {e}")
        return False


def main():
    logger.console_print("\n" + "=" * 60)
    logger.console_print(f"{'SomPlus Scheduler':^60}")
    logger.console_print("=" * 60 + "\n")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config", "app.json")

    logger.console_info(f"Loading configuration from: {config_path}")
    try:
        app_config = load_json(config_path)
    except Exception as e:
        logger.console_error(f"Failed to load configuration: {e}")
        sys.exit(1)

    if "scheduler" not in app_config or "sleep_schedule" not in app_config["scheduler"]:
        logger.console_error("No sleep_schedule found in app.json under 'scheduler'")
        sys.exit(1)

    sleep_schedule = app_config["scheduler"]["sleep_schedule"]
    logger.console_success(f"Loaded {len(sleep_schedule)} time window(s)")

    logger.console_print("\nTime windows:")
    for i, window in enumerate(sleep_schedule, 1):
        start = f"{window['start'][0]:02d}:{window['start'][1]:02d}"
        end = f"{window['end'][0]:02d}:{window['end'][1]:02d}"
        logger.console_print(f"  {i}. {start} - {end}: check every {window['sleep']}s", indent=2)

    logger.console_print("\n" + "=" * 60)
    logger.console_success("Scheduler started - running continuously")
    logger.console_print("=" * 60 + "\n")

    cycle = 0
    while True:
        cycle += 1
        current_sleep = get_current_time_window(sleep_schedule)
        now = datetime.now()

        logger.console_print(f"\n{'─' * 60}")
        logger.console_info(f"Cycle #{cycle} - {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.console_print(f"Current interval: {current_sleep}s", indent=2)
        logger.console_print(f"{'─' * 60}")

        success = run_monitor()

        if success:
            logger.console_success("Monitor completed successfully")
        else:
            logger.console_error("Monitor completed with errors")

        logger.console_print(f"\nSleeping for {current_sleep}s until next check...\n")
        time.sleep(current_sleep)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.console_print("\n\n" + "=" * 60)
        logger.console_info("Scheduler stopped by user")
        logger.console_print("=" * 60 + "\n")
        sys.exit(0)
    except Exception as e:
        logger.console_error(f"Scheduler crashed: {e}")
        sys.exit(1)
