import requests
from lib.utils import config, logger


class PushSaferNotifier:
    def is_enabled(self, user_config):
        return config.get_pushsafer_grades_enabled(
            user_config
        ) or config.get_pushsafer_schedule_enabled(user_config)

    def send_grade_notification(self, username, user_config, change):
        if not config.get_pushsafer_grades_enabled(user_config):
            return

        change_type = change.get("type", "NEW")

        if change_type == "NEW_HERKANSING":
            grade = change["grade"]
            additional = grade.get("additionalObjects", {})
            subject = additional.get("vaknaam", "")
            test_name = grade.get("omschrijving", "")

            original_result = change.get("original_result", "?")
            herkansing_result = change.get("herkansing_result", "?")
            geldig_result = grade.get("formattedResultaat", "?")

            try:
                orig_num = float(str(original_result).replace(",", "."))
                herk_num = float(str(herkansing_result).replace(",", "."))
                if herk_num > orig_num:
                    sound = config.get_pushsafer_grades_sound_high(user_config)
                else:
                    sound = config.get_pushsafer_grades_sound_low(user_config)
            except (ValueError, AttributeError):
                sound = config.get_pushsafer_grades_sound_medium(user_config)

            title = f"Herkansing: {original_result} → {herkansing_result}"
            message = (
                f"{subject}\n"
                f"{test_name}\n"
                f"Origineel cijfer: {original_result}\n"
                f"Herkansing: {herkansing_result}\n"
                f"Geldig cijfer: {geldig_result}\n"
                f"Weging: {grade.get('weging', '?')}\n"
                f"Periode {grade.get('periode', '?')}\n"
                f"Type: {grade.get('herkansing', '?')}"
            )

        elif change_type == "NEW":
            grade = change["grade"]
            additional = grade.get("additionalObjects", {})
            grade_value = grade.get("formattedResultaat", "") or grade.get("label", "")
            subject = additional.get("vaknaam", "")
            test_name = grade.get("omschrijving", "")

            try:
                numeric_grade = float(str(grade_value).replace(",", "."))
                breakpoint_high = config.get_pushsafer_grades_breakpoint_high(
                    user_config
                )
                breakpoint_medium = config.get_pushsafer_grades_breakpoint_medium(
                    user_config
                )

                if numeric_grade >= breakpoint_high:
                    sound = config.get_pushsafer_grades_sound_high(user_config)
                elif numeric_grade >= breakpoint_medium:
                    sound = config.get_pushsafer_grades_sound_medium(user_config)
                else:
                    sound = config.get_pushsafer_grades_sound_low(user_config)
            except (ValueError, AttributeError):
                sound = config.get_pushsafer_grades_sound_medium(user_config)

            title = f"Nieuw cijfer: {grade_value}"
            message_parts = [
                subject,
                test_name,
                f"Cijfer: {grade_value}",
                f"Periode {grade.get('periode', '?')}",
                f"Weging: {grade.get('weging', '?')}",
            ]

            if grade.get("toetssoort"):
                message_parts.append(f"Toetssoort: {grade.get('toetssoort')}")

            flags = []
            if grade.get("isLabel"):
                flags.append("label cijfer")
            if not grade.get("isVoldoende"):
                flags.append("onvoldoende")

            if flags:
                message_parts.append(", ".join(flags))

            if grade.get("herkansing") and grade.get("herkansing") != "Geen":
                message_parts.append(f"Herkansbaar: {grade.get('herkansing')}")

            message = "\n".join(message_parts)

        elif change_type == "CHANGED":
            old_grade = change["old_grade"]
            new_grade = change["new_grade"]
            grade_changes = change.get("changes", {})

            additional = new_grade.get("additionalObjects", {})
            subject = additional.get("vaknaam", "")
            test_name = new_grade.get("omschrijving", "")

            changes_list = []
            sound = config.get_pushsafer_grades_sound_medium(user_config)

            if "resultaat" in grade_changes:
                old_value = grade_changes["resultaat"]["old"]
                new_value = grade_changes["resultaat"]["new"]

                try:
                    old_numeric = float(str(old_value).replace(",", "."))
                    new_numeric = float(str(new_value).replace(",", "."))
                    diff = new_numeric - old_numeric

                    if new_numeric > old_numeric:
                        sound = config.get_pushsafer_grades_sound_high(user_config)
                        changes_list.append(
                            f"Cijfer: {old_value} → {new_value} (+{diff:.1f})"
                        )
                    else:
                        sound = config.get_pushsafer_grades_sound_low(user_config)
                        changes_list.append(
                            f"Cijfer: {old_value} → {new_value} ({diff:.1f})"
                        )
                except (ValueError, AttributeError):
                    changes_list.append(f"Cijfer: {old_value} → {new_value}")

            if "herkansing_resultaat" in grade_changes:
                old_h = grade_changes["herkansing_resultaat"]["old"]
                new_h = grade_changes["herkansing_resultaat"]["new"]
                changes_list.append(f"Herkansing: {old_h} → {new_h}")

            if "weging" in grade_changes:
                old_w = grade_changes["weging"]["old"]
                new_w = grade_changes["weging"]["new"]
                changes_list.append(f"weging: {old_w} → {new_w}")

            if "periode" in grade_changes:
                old_p = grade_changes["periode"]["old"]
                new_p = grade_changes["periode"]["new"]
                changes_list.append(f"periode: {old_p} → {new_p}")

            title = f"Cijfer gewijzigd: {subject}"
            current_grade = new_grade.get("formattedResultaat", "?")
            message = (
                f"{subject}\n"
                f"{test_name}\n"
                f"Huidig cijfer: {current_grade}\n"
                f"Periode {new_grade.get('periode', '?')}\n"
                f"\nWijzigingen:\n" + "\n".join(changes_list)
            )

        elif change_type == "REMOVED":
            grade = change["grade"]
            additional = grade.get("additionalObjects", {})
            grade_value = grade.get("formattedResultaat", "")
            subject = additional.get("vaknaam", "")
            test_name = grade.get("omschrijving", "")

            sound = config.get_pushsafer_grades_sound_low(user_config)
            title = f"Cijfer verwijderd: {grade_value}"
            message = (
                f"{subject}\n"
                f"{test_name}\n"
                f"Verwijderd cijfer: {grade_value}\n"
                f"Periode {grade.get('periode', '?')}\n"
                f"Weging: {grade.get('weging', '?')}\n"
                f"Toetssoort: {grade.get('toetssoort', '?')}"
            )

        else:
            return

        self.send_notification(
            user_config,
            "grades",
            title=title,
            message=message,
            sound=sound,
            icon=config.get_pushsafer_grades_icon(user_config),
            priority=config.get_pushsafer_grades_priority(user_config),
        )

    def send_schedule_notification(
        self, username, user_config, changes, current_schedule, rolled_over=False
    ):
        if not config.get_pushsafer_schedule_enabled(user_config):
            return

        changes_text = self.format_changes_detailed(changes, current_schedule)

        title = f"Rooster gewijzigd ({len(changes)} wijziging{'en' if len(changes) != 1 else ''})"
        message = changes_text

        self.send_notification(
            user_config,
            "schedule",
            title=title,
            message=message,
            sound=config.get_pushsafer_schedule_sound(user_config),
            icon=config.get_pushsafer_schedule_icon(user_config),
            priority=config.get_pushsafer_schedule_priority(user_config),
        )

    def send_error_notification(self, username, user_config, error_list):
        if not config.get_pushsafer_errors_enabled(user_config):
            return

        error_count = sum(e.get("count", 1) for e in error_list)

        lines = []
        for entry in error_list:
            line = entry["message"]
            if entry.get("count", 1) > 1:
                line += f" (x{entry['count']})"
            lines.append(line)

        title = f"Fouten ({error_count})"
        message = "\n".join(lines)

        self.send_notification(
            user_config,
            "errors",
            title=title,
            message=message,
            sound=config.get_pushsafer_errors_sound(user_config),
            icon=config.get_pushsafer_errors_icon(user_config),
            priority=config.get_pushsafer_errors_priority(user_config),
        )

    def send_notification(
        self, user_config, notification_type, title, message, sound, icon, priority
    ):
        url = "https://www.pushsafer.com/api"

        if notification_type == "grades":
            api_key = config.get_pushsafer_grades_api_key(user_config)
            device_id = config.get_pushsafer_grades_device_id(user_config)
        elif notification_type == "schedule":
            api_key = config.get_pushsafer_schedule_api_key(user_config)
            device_id = config.get_pushsafer_schedule_device_id(user_config)
        elif notification_type == "errors":
            api_key = config.get_pushsafer_errors_api_key(user_config)
            device_id = config.get_pushsafer_errors_device_id(user_config)
        else:
            return

        params = {
            "k": api_key,
            "d": device_id,
            "t": title,
            "m": message,
            "s": str(sound),
            "i": str(icon),
            "pr": str(priority),
            "u": "somtoday://",
            "ut": "SOMTODAY",
        }

        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
        except Exception as e:
            logger.log_warning("system", f"PushSafer notification failed: {e}")
            raise

    def format_changes_detailed(self, changes, current_schedule):
        day_names_short = ["ma", "di", "wo", "do", "vr"]

        lessons_by_day = {}
        if current_schedule and "lessons" in current_schedule:
            for lesson in current_schedule["lessons"]:
                day = lesson["day"]
                if day not in lessons_by_day:
                    lessons_by_day[day] = []
                lessons_by_day[day].append(lesson)

        change_texts = []
        for change in changes:
            day = change["day"]
            day_name = day_names_short[day]

            if change["type"] == "UITVAL":
                change_texts.append(f"{day_name}: {change['subject']} uitval")
            elif change["type"] == "COMPLETE_UITVAL":
                change_texts.append(f"{day_name}: {change['subject']} complete uitval")
            elif change["type"] == "GEDEELTELIJKE_UITVAL":
                count = change.get("count", 1)
                change_texts.append(
                    f"{day_name}: {change['subject']} -{count} les{'sen' if count > 1 else ''}"
                )
            elif change["type"] == "ANTI_UITVAL":
                count = change.get("count", 1)
                change_texts.append(
                    f"{day_name}: {change['subject']} +{count} extra les{'sen' if count > 1 else ''}"
                )
            elif change["type"] == "SUBJECT_CHANGE":
                period = change.get("period", "?")
                old = change["old"]
                new = change["new"]
                change_texts.append(f"{day_name} {period}e uur: {old} -> {new}")
            elif change["type"] == "TEACHER_CHANGE":
                period = change.get("period", "?")
                subject = change["subject"]
                old_teacher = change["old"]
                new_teacher = change["new"]
                change_texts.append(
                    f"{day_name} {period}e {subject}: docent {old_teacher} -> {new_teacher}"
                )
            elif change["type"] == "LOCATION_CHANGE":
                period = change.get("period", "?")
                subject = change["subject"]
                old_loc = change["old"]
                new_loc = change["new"]
                change_texts.append(
                    f"{day_name} {period}e {subject}: lokaal {old_loc} -> {new_loc}"
                )

        result = "\n".join(change_texts)

        changed_days = set(c["day"] for c in changes)
        if changed_days:
            result += "\n\nvandaag:\n"
            today_lessons = lessons_by_day.get(0, [])
            if today_lessons:
                today_lessons.sort(key=lambda x: x["period"])
                for lesson in today_lessons:
                    if lesson["subject"]:
                        result += f"{lesson['period']}e: {lesson['subject']} ({lesson['teacher']}, {lesson['location']})\n"
            else:
                result += "Geen lessen\n"

        return result
