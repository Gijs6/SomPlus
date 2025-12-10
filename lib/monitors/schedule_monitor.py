from datetime import datetime, timedelta
from collections import Counter
from lib.monitors.base_monitor import BaseMonitor
from lib.utils import config, logger


class ScheduleMonitor(BaseMonitor):
    def is_enabled(self):
        return config.get_schedule_enabled(self.user_config)

    def run(self, access_token, notifiers):
        if not self.is_enabled():
            logger.console_info(
                f"{self.__class__.__name__} is disabled, skipping", indent=4
            )
            return

        logger.console_print("Fetching current week data...", indent=4)
        try:
            raw_data = self.fetch_data(access_token)
        except Exception as e:
            logger.console_error(f"Failed to fetch data: {e}", indent=4)
            return

        logger.console_print("Processing data...", indent=4)
        try:
            processed_data = self.process_data(raw_data)
        except Exception as e:
            logger.console_error(f"Failed to process data: {e}", indent=4)
            return

        logger.console_print("Loading cached data...", indent=4)
        cached_data = self.load_cached_data()

        if cached_data is None:
            logger.console_info("Initializing cache...", indent=4)
            self.save_data(processed_data)
            return

        logger.console_print("Comparing with cached data...", indent=4)
        try:
            changes = self.compare_data(cached_data, processed_data, access_token)
        except Exception as e:
            logger.console_error(f"Failed to compare data: {e}", indent=4)
            return

        if changes:
            change_count = len(changes) if isinstance(changes, list) else 1
            logger.console_print(
                f"Found {change_count} change(s), saving data...", indent=4
            )
            self.save_data(processed_data)
            logger.console_print("Sending notifications...", indent=4)
            try:
                self.notify_changes(changes, notifiers)
                logger.console_success("Saved data and sent notifications", indent=4)
            except Exception as e:
                logger.console_error(f"Failed to send notifications: {e}", indent=4)
        else:
            logger.console_info("No changes detected", indent=4)
            self.save_data(processed_data)

    def fetch_data(self, access_token):
        monday, saturday, week_number = self.get_week_dates()
        raw_schedule = self.api.fetch_schedule(access_token, monday, saturday)
        return raw_schedule

    def clean_nested_object(self, obj):
        if not isinstance(obj, dict):
            return obj

        cleaned = {}
        for k, v in obj.items():
            if k in ["links", "permissions", "$type"]:
                continue
            if k == "additionalObjects" and (not v or v == {}):
                continue

            if isinstance(v, dict):
                cleaned[k] = self.clean_nested_object(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    self.clean_nested_object(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                cleaned[k] = v

        return cleaned

    def process_data(self, raw_data):
        processed_lessons = []
        filters = config.get_schedule_filters(self.user_config)

        for entry in raw_data:
            clean_entry = self.clean_nested_object(entry)
            begin_lesuur = clean_entry.get("beginLesuur")
            eind_lesuur = clean_entry.get("eindLesuur")

            if begin_lesuur is None or eind_lesuur is None:
                continue

            vakken = clean_entry.get("vakken", [])
            has_subject = False
            if vakken:
                has_subject = True
            else:
                titel = clean_entry.get("titel", "")
                if titel:
                    parts = [p.strip() for p in titel.split("-")]
                    if len(parts) >= 2:
                        has_subject = True

            if not has_subject:
                continue

            processed_lessons.append(clean_entry)

        return processed_lessons

    def get_week_dates(self):
        now = datetime.now()

        rollover_hour = config.get_weekend_rollover_hour(self.user_config)
        rollover_day = config.get_weekend_rollover_day(self.user_config)
        schedule_end_day = config.get_schedule_fetch_end_day(self.user_config)

        if now.weekday() == rollover_day and now.hour >= rollover_hour:
            days_to_add = 7 - rollover_day
            now = now + timedelta(days=days_to_add)
        elif now.weekday() > rollover_day:
            days_until_monday = 7 - now.weekday()
            now = now + timedelta(days=days_until_monday)

        monday = now - timedelta(days=now.weekday())
        end_day = monday + timedelta(days=schedule_end_day)

        week_number = monday.isocalendar()[1]

        monday_str = monday.strftime("%Y-%m-%d")
        end_day_str = end_day.strftime("%Y-%m-%d")

        return monday_str, end_day_str, str(week_number)

    def load_cached_data(self):
        path = self.get_user_data_path("schedule.json")
        return self.load_json_file(path)

    def save_data(self, data):
        path = self.get_user_data_path("schedule.json")
        self.save_json_file(path, data)

    def compare_data(self, old_data, new_data, access_token):
        monday, saturday, current_week = self.get_week_dates()

        old_week = None
        if old_data:
            for entry in old_data:
                begin_datum_tijd = entry.get("beginDatumTijd", "")
                if begin_datum_tijd:
                    try:
                        dt = datetime.strptime(
                            begin_datum_tijd, "%Y-%m-%dT%H:%M:%S.%f%z"
                        )
                        old_week = str(dt.isocalendar()[1])
                        break
                    except (ValueError, AttributeError):
                        pass

        if old_week != current_week:
            logger.console_info(
                f"Week changed from {old_week} to {current_week}", indent=4
            )
            logger.console_print("Generating standard schedule on-the-fly...", indent=4)
            standard_schedule = self.find_best_standard_schedule(access_token)
            if not standard_schedule:
                logger.console_warning(
                    "Could not generate standard schedule, using empty baseline",
                    indent=4,
                )
                old_lessons = []
            else:
                old_lessons = standard_schedule
        else:
            old_lessons = old_data

        new_lessons = new_data
        changes = self.compare_schedules(old_lessons, new_lessons)

        return changes

    def extract_lesson_info(self, entry):
        vakken = entry.get("vakken", [])
        if vakken:
            subject = vakken[0].get("afkorting", "")
        else:
            subject = ""

        docenten = entry.get("docenten", [])
        if docenten:
            teacher = docenten[0].get("afkorting", "")
        else:
            teacher = ""

        locatie = entry.get("locatie", "")

        if not subject or not teacher:
            titel = entry.get("titel", "")
            if titel:
                parts = [p.strip() for p in titel.split("-")]
                if len(parts) >= 3:
                    if not locatie:
                        locatie = parts[0]
                    if not subject:
                        subject = parts[1]
                    if not teacher:
                        teacher = parts[2]
                elif len(parts) == 2:
                    if not subject:
                        subject = parts[0]
                    if not teacher:
                        teacher = parts[1]

        begin_datum_tijd = entry.get("beginDatumTijd", "")
        if begin_datum_tijd:
            try:
                dt = datetime.strptime(begin_datum_tijd, "%Y-%m-%dT%H:%M:%S.%f%z")
                day_index = dt.weekday()
            except (ValueError, AttributeError):
                day_index = 0
        else:
            day_index = 0

        period = entry.get("beginLesuur")

        return {
            "subject": subject,
            "teacher": teacher,
            "location": locatie,
            "day": day_index,
            "period": period,
        }

    def compare_schedules(self, old_lessons, new_lessons):
        changes = []

        for day in range(5):
            old_day = [
                l for l in old_lessons if self.extract_lesson_info(l)["day"] == day
            ]
            new_day = [
                l for l in new_lessons if self.extract_lesson_info(l)["day"] == day
            ]

            old_subjects = Counter(
                [
                    self.extract_lesson_info(l)["subject"]
                    for l in old_day
                    if self.extract_lesson_info(l)["subject"]
                ]
            )
            new_subjects = Counter(
                [
                    self.extract_lesson_info(l)["subject"]
                    for l in new_day
                    if self.extract_lesson_info(l)["subject"]
                ]
            )

            all_subjects = set(old_subjects.keys()) | set(new_subjects.keys())
            for subject in all_subjects:
                old_count = old_subjects.get(subject, 0)
                new_count = new_subjects.get(subject, 0)

                if old_count > new_count:
                    diff = old_count - new_count
                    if new_count == 0:
                        if old_count == 1:
                            changes.append(
                                {"day": day, "type": "UITVAL", "subject": subject}
                            )
                        else:
                            changes.append(
                                {
                                    "day": day,
                                    "type": "COMPLETE_UITVAL",
                                    "subject": subject,
                                    "count": old_count,
                                }
                            )
                    else:
                        changes.append(
                            {
                                "day": day,
                                "type": "GEDEELTELIJKE_UITVAL",
                                "subject": subject,
                                "count": diff,
                            }
                        )

                if old_count < new_count:
                    diff = new_count - old_count
                    changes.append(
                        {
                            "day": day,
                            "type": "ANTI_UITVAL",
                            "subject": subject,
                            "count": diff,
                        }
                    )

            old_by_period = {}
            for l in old_day:
                info = self.extract_lesson_info(l)
                key = info["period"]
                if key and key not in old_by_period:
                    old_by_period[key] = []
                if key:
                    old_by_period[key].append((l, info))

            new_by_period = {}
            for l in new_day:
                info = self.extract_lesson_info(l)
                key = info["period"]
                if key and key not in new_by_period:
                    new_by_period[key] = []
                if key:
                    new_by_period[key].append((l, info))

            for period in set(old_by_period.keys()) & set(new_by_period.keys()):
                old_lessons_in_period = old_by_period[period]
                new_lessons_in_period = new_by_period[period]

                for old_lesson, old_info in old_lessons_in_period:
                    matching_new = [
                        (nl, ninfo)
                        for nl, ninfo in new_lessons_in_period
                        if ninfo["subject"] == old_info["subject"]
                    ]

                    if not matching_new:
                        for new_lesson, new_info in new_lessons_in_period:
                            if new_info["subject"]:
                                changes.append(
                                    {
                                        "day": day,
                                        "period": period,
                                        "type": "SUBJECT_CHANGE",
                                        "old": old_info["subject"],
                                        "new": new_info["subject"],
                                    }
                                )
                                break
                    else:
                        new_lesson, new_info = matching_new[0]
                        if old_info["teacher"] != new_info["teacher"]:
                            changes.append(
                                {
                                    "day": day,
                                    "period": period,
                                    "type": "TEACHER_CHANGE",
                                    "subject": old_info["subject"],
                                    "old": old_info["teacher"],
                                    "new": new_info["teacher"],
                                }
                            )
                        if old_info["location"] != new_info["location"]:
                            changes.append(
                                {
                                    "day": day,
                                    "period": period,
                                    "type": "LOCATION_CHANGE",
                                    "subject": old_info["subject"],
                                    "old": old_info["location"],
                                    "new": new_info["location"],
                                }
                            )

        return changes

    def find_best_standard_schedule(self, access_token):
        weeks_to_check = config.get_standard_schedule_weeks_ahead(self.user_config)
        logger.console_print(
            f"Searching for best standard schedule (checking {weeks_to_check} weeks ahead)...",
            indent=4,
        )

        now = datetime.now()
        best_week = None
        max_lesson_count = 0
        best_week_number = None

        for week_offset in range(weeks_to_check):
            check_date = now + timedelta(weeks=week_offset)
            monday = check_date - timedelta(days=check_date.weekday())
            saturday = monday + timedelta(days=5)
            week_number = monday.isocalendar()[1]

            monday_str = monday.strftime("%Y-%m-%d")
            saturday_str = saturday.strftime("%Y-%m-%d")

            try:
                raw_schedule = self.api.fetch_schedule(
                    access_token, monday_str, saturday_str
                )
                processed = self.process_data(raw_schedule)
                lesson_count = len(processed)

                logger.console_print(
                    f"Week {week_number} ({monday_str}): {lesson_count} lessons",
                    indent=6,
                )

                if lesson_count > max_lesson_count:
                    max_lesson_count = lesson_count
                    best_week = processed
                    best_week_number = week_number

            except Exception as e:
                logger.console_error(
                    f"Week {week_number}: Failed to fetch ({e})", indent=6
                )
                continue

        if best_week:
            logger.console_success(
                f"Best standard schedule found with {max_lesson_count} lessons (week {best_week_number})",
                indent=4,
            )
            return best_week

        return None

    def notify_changes(self, changes, notifiers):
        if not changes:
            return

        current_schedule = self.load_cached_data()

        current_schedule_display = {"lessons": []}

        if current_schedule:
            for entry in current_schedule:
                info = self.extract_lesson_info(entry)

                begin_datum_tijd = entry.get("beginDatumTijd", "")
                eind_datum_tijd = entry.get("eindDatumTijd", "")

                if begin_datum_tijd:
                    try:
                        dt_start = datetime.strptime(
                            begin_datum_tijd, "%Y-%m-%dT%H:%M:%S.%f%z"
                        )
                        start_time = dt_start.strftime("%H:%M")
                    except (ValueError, AttributeError):
                        start_time = ""
                else:
                    start_time = ""

                if eind_datum_tijd:
                    try:
                        dt_end = datetime.strptime(
                            eind_datum_tijd, "%Y-%m-%dT%H:%M:%S.%f%z"
                        )
                        end_time = dt_end.strftime("%H:%M")
                    except (ValueError, AttributeError):
                        end_time = ""
                else:
                    end_time = ""

                current_schedule_display["lessons"].append(
                    {
                        "day": info["day"],
                        "period": info["period"],
                        "period_end": entry.get("eindLesuur"),
                        "subject": info["subject"],
                        "teacher": info["teacher"],
                        "location": info["location"],
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                )

        for notifier in notifiers:
            notifier.send_schedule_notification(
                self.username, self.user_config, changes, current_schedule_display
            )
