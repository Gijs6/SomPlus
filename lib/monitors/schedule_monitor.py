from datetime import datetime, timedelta
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
            raw_data, rolled_over = self.fetch_data(access_token)
        except Exception as e:
            logger.log_error(
                self.username, f"{self.__class__.__name__} failed to fetch data", e
            )
            return

        logger.console_print("Processing data...", indent=4)
        try:
            processed_data = self.process_data(raw_data)
        except Exception as e:
            logger.log_error(
                self.username, f"{self.__class__.__name__} failed to process data", e
            )
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
            logger.log_error(
                self.username, f"{self.__class__.__name__} failed to compare data", e
            )
            return

        if changes:
            change_count = len(changes) if isinstance(changes, list) else 1
            logger.console_print(
                f"Found {change_count} change(s), sending notifications...", indent=4
            )
            try:
                self.notify_changes(changes, notifiers, rolled_over)
                logger.console_success("Notifications sent", indent=4)
            except Exception as e:
                logger.log_error(
                    self.username,
                    f"{self.__class__.__name__} failed to send notifications",
                    e,
                )
                logger.console_warning(
                    "Skipping cache save so changes are retried next run", indent=4
                )
                return
            self.save_data(processed_data)
            logger.console_success("Data saved", indent=4)
        else:
            logger.console_info("No changes detected", indent=4)
            self.save_data(processed_data)

    def fetch_data(self, access_token):
        monday, saturday, week_number, rolled_over = self.get_week_dates()
        raw_schedule = self.api.fetch_schedule(access_token, monday, saturday)
        return raw_schedule, rolled_over

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
        exclude_subjects = filters.get("exclude_subjects", [])

        for entry in raw_data:
            clean_entry = self.clean_nested_object(entry)
            begin_lesuur = clean_entry.get("beginLesuur")
            eind_lesuur = clean_entry.get("eindLesuur")

            if begin_lesuur is None or eind_lesuur is None:
                continue

            vakken = clean_entry.get("vakken", [])
            subject_name = ""
            has_subject = False
            if vakken:
                has_subject = True
                subject_name = vakken[0].get("afkorting", "")
            else:
                titel = clean_entry.get("titel", "")
                if titel:
                    parts = [p.strip() for p in titel.split("-")]
                    if len(parts) >= 3:
                        has_subject = True
                        subject_name = parts[1]
                    elif len(parts) == 2:
                        has_subject = True
                        subject_name = parts[0]

            if not has_subject:
                continue

            if subject_name and subject_name in exclude_subjects:
                continue

            processed_lessons.append(clean_entry)

        return processed_lessons

    def get_week_dates(self):
        now = datetime.now()

        rollover_hour = config.get_weekend_rollover_hour(self.user_config)
        rollover_day = config.get_weekend_rollover_day(self.user_config)
        schedule_end_day = config.get_schedule_fetch_end_day(self.user_config)

        rolled_over = False
        if now.weekday() == rollover_day and now.hour >= rollover_hour:
            rolled_over = True
            days_to_add = 7 - rollover_day
            now = now + timedelta(days=days_to_add)
        elif now.weekday() > rollover_day:
            rolled_over = True
            days_until_monday = 7 - now.weekday()
            now = now + timedelta(days=days_until_monday)

        monday = now - timedelta(days=now.weekday())
        end_day = monday + timedelta(days=schedule_end_day)

        week_number = monday.isocalendar()[1]

        monday_str = monday.strftime("%Y-%m-%d")
        end_day_str = end_day.strftime("%Y-%m-%d")

        return monday_str, end_day_str, str(week_number), rolled_over

    def load_cached_data(self):
        path = self.get_user_data_path("schedule.json")
        return self.load_json_file(path)

    def save_data(self, data):
        path = self.get_user_data_path("schedule.json")
        self.save_json_file(path, data)

    def compare_data(self, old_data, new_data, access_token):
        monday, saturday, current_week, _ = self.get_week_dates()

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
                    "Could not generate standard schedule, skipping comparison",
                    indent=4,
                )
                return []
            else:
                old_lessons = standard_schedule
        else:
            old_lessons = old_data

        new_lessons = new_data
        changes = self.compare_schedules(old_lessons, new_lessons)

        return changes

    def get_lesson_hours(self, entry):
        begin = entry.get("beginLesuur")
        end = entry.get("eindLesuur")

        if begin is None or end is None:
            return 1

        return (end - begin) + 1

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
            old_day_info = [
                (l, self.extract_lesson_info(l))
                for l in old_lessons
                if self.extract_lesson_info(l)["day"] == day
            ]
            new_day_info = [
                (l, self.extract_lesson_info(l))
                for l in new_lessons
                if self.extract_lesson_info(l)["day"] == day
            ]

            old_subject_hours = {}
            for lesson, info in old_day_info:
                subject = info["subject"]
                if subject:
                    hours = self.get_lesson_hours(lesson)
                    old_subject_hours[subject] = (
                        old_subject_hours.get(subject, 0) + hours
                    )

            new_subject_hours = {}
            for lesson, info in new_day_info:
                subject = info["subject"]
                if subject:
                    hours = self.get_lesson_hours(lesson)
                    new_subject_hours[subject] = (
                        new_subject_hours.get(subject, 0) + hours
                    )

            all_subjects = set(old_subject_hours.keys()) | set(new_subject_hours.keys())
            for subject in all_subjects:
                old_hours = old_subject_hours.get(subject, 0)
                new_hours = new_subject_hours.get(subject, 0)

                if old_hours > new_hours:
                    diff = old_hours - new_hours
                    if new_hours == 0:
                        if old_hours == 1:
                            changes.append(
                                {"day": day, "type": "UITVAL", "subject": subject}
                            )
                        else:
                            changes.append(
                                {
                                    "day": day,
                                    "type": "COMPLETE_UITVAL",
                                    "subject": subject,
                                    "count": old_hours,
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

                if old_hours < new_hours:
                    diff = new_hours - old_hours
                    changes.append(
                        {
                            "day": day,
                            "type": "ANTI_UITVAL",
                            "subject": subject,
                            "count": diff,
                        }
                    )

            old_subject_periods = {}
            for lesson, info in old_day_info:
                subject = info["subject"]
                if subject and info["period"] is not None:
                    old_subject_periods.setdefault(subject, set()).add(info["period"])

            new_subject_periods = {}
            for lesson, info in new_day_info:
                subject = info["subject"]
                if subject and info["period"] is not None:
                    new_subject_periods.setdefault(subject, set()).add(info["period"])

            for subject in all_subjects:
                old_hours = old_subject_hours.get(subject, 0)
                new_hours = new_subject_hours.get(subject, 0)
                if old_hours == new_hours and old_hours > 0:
                    old_periods = old_subject_periods.get(subject, set())
                    new_periods = new_subject_periods.get(subject, set())
                    if old_periods != new_periods:
                        changes.append(
                            {
                                "day": day,
                                "type": "VERPLAATSING",
                                "subject": subject,
                                "old_periods": sorted(old_periods),
                                "new_periods": sorted(new_periods),
                            }
                        )

            for subject in all_subjects:
                if subject not in old_subject_hours or subject not in new_subject_hours:
                    continue

                old_subject_lessons = [
                    info for _, info in old_day_info if info["subject"] == subject
                ]
                new_subject_lessons = [
                    info for _, info in new_day_info if info["subject"] == subject
                ]

                old_teachers = set(
                    i["teacher"] for i in old_subject_lessons if i["teacher"]
                )
                new_teachers = set(
                    i["teacher"] for i in new_subject_lessons if i["teacher"]
                )
                old_locations = set(
                    i["location"] for i in old_subject_lessons if i["location"]
                )
                new_locations = set(
                    i["location"] for i in new_subject_lessons if i["location"]
                )

                if old_teachers != new_teachers and old_teachers and new_teachers:
                    changes.append(
                        {
                            "day": day,
                            "type": "TEACHER_CHANGE",
                            "subject": subject,
                            "old": ", ".join(sorted(old_teachers)),
                            "new": ", ".join(sorted(new_teachers)),
                        }
                    )

                if old_locations != new_locations and old_locations and new_locations:
                    changes.append(
                        {
                            "day": day,
                            "type": "LOCATION_CHANGE",
                            "subject": subject,
                            "old": ", ".join(sorted(old_locations)),
                            "new": ", ".join(sorted(new_locations)),
                        }
                    )

            old_by_period = {}
            for l, info in old_day_info:
                key = info["period"]
                if key is not None:
                    old_by_period.setdefault(key, []).append((l, info))

            new_by_period = {}
            for l, info in new_day_info:
                key = info["period"]
                if key is not None:
                    new_by_period.setdefault(key, []).append((l, info))

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
                logger.log_warning(
                    self.username, f"Failed to fetch schedule for week {week_number}", e
                )
                continue

        if best_week:
            logger.console_success(
                f"Best standard schedule found with {max_lesson_count} lessons (week {best_week_number})",
                indent=4,
            )
            return best_week

        return None

    def notify_changes(self, changes, notifiers, rolled_over=False):
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
                self.username,
                self.user_config,
                changes,
                current_schedule_display,
                rolled_over,
            )
