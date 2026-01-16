import requests
from datetime import datetime
from lib.utils import config, logger


class DiscordNotifier:
    def is_enabled(self, user_config):
        return config.get_discord_grades_enabled(
            user_config
        ) or config.get_discord_schedule_enabled(user_config)

    def send_grade_notification(self, username, user_config, change):
        if not config.get_discord_grades_enabled(user_config):
            return

        display_name = user_config["display_name"]
        change_type = change.get("type", "NEW")

        if change_type == "NEW_HERKANSING":
            grade = change["grade"]
            subject = grade.get("vak", {}).get("afkorting", "")
            subject_naam = grade.get("vak", {}).get("naam", subject)
            test_name = grade.get("omschrijving", "onbekend")

            original_result = change.get("original_result", "?")
            herkansing_result = change.get("herkansing_result", "?")
            geldig_result = grade.get("geldendResultaat") or grade.get("resultaat", "?")

            try:
                orig_num = float(str(original_result).replace(",", "."))
                herk_num = float(str(herkansing_result).replace(",", "."))
                diff = herk_num - orig_num

                if orig_num != 0:
                    pct_change = (diff / orig_num) * 100
                    pct_str = f", {pct_change:+.1f}%"
                else:
                    pct_str = ""

                if herk_num > orig_num:
                    color = config.get_discord_grades_color_high(user_config)
                    improvement = f"+{diff:.1f}{pct_str}"
                elif herk_num < orig_num:
                    color = config.get_discord_grades_color_low(user_config)
                    improvement = f"{diff:.1f}{pct_str}"
                else:
                    color = config.get_discord_grades_color_medium(user_config)
                    improvement = "±0.0"
            except (ValueError, AttributeError):
                color = config.get_discord_grades_color(user_config)
                improvement = "?"

            content = f"**Herkansing** voor {subject}: {original_result} → {herkansing_result} ({improvement})"
            mention_role_id = config.get_discord_grades_mention_role_id(user_config)
            if mention_role_id:
                content += f" - <@&{mention_role_id}>"

            fields = [
                {
                    "name": "Origineel cijfer",
                    "value": f"~~{original_result}~~",
                    "inline": True,
                },
                {
                    "name": "Herkansing",
                    "value": f"**{herkansing_result}**",
                    "inline": True,
                },
                {
                    "name": "Geldig cijfer",
                    "value": f"**{geldig_result}**",
                    "inline": True,
                },
                {"name": "Vak", "value": f"{subject} - {subject_naam}", "inline": True},
                {
                    "name": "Weging",
                    "value": str(grade.get("weging", "?")),
                    "inline": True,
                },
                {
                    "name": "Examen weging",
                    "value": str(grade.get("examenWeging", "?")),
                    "inline": True,
                },
                {
                    "name": "Periode",
                    "value": str(grade.get("periode", "?")),
                    "inline": True,
                },
                {
                    "name": "Leerjaar",
                    "value": str(grade.get("leerjaar", "?")),
                    "inline": True,
                },
                {
                    "name": "Type",
                    "value": grade.get("herkansingstype", "?"),
                    "inline": True,
                },
            ]

            embed = {
                "title": f"Nieuwe herkansing voor {display_name}",
                "description": f"**{subject}** - {test_name}",
                "color": color,
                "fields": fields,
                "footer": {"text": "SomPlus"},
            }

            payload = {
                "content": content,
                "tts": config.get_discord_grades_tts(user_config),
                "embeds": [embed],
            }

            webhook_url = config.get_discord_grades_webhook_url(user_config)
            self.send_webhook(webhook_url, payload)

        elif change_type == "NEW":
            grade = change["grade"]
            grade_value = (
                grade.get("geldendResultaat")
                or grade.get("resultaat")
                or grade.get("resultaatLabelAfkorting", "")
            )
            subject = grade.get("vak", {}).get("afkorting", "")
            subject_naam = grade.get("vak", {}).get("naam", subject)
            test_name = grade.get("omschrijving", "onbekend")

            try:
                numeric_grade = float(str(grade_value).replace(",", "."))
                breakpoint_high = config.get_discord_grades_breakpoint_high(user_config)
                breakpoint_medium = config.get_discord_grades_breakpoint_medium(
                    user_config
                )

                if numeric_grade >= breakpoint_high:
                    color = config.get_discord_grades_color_high(user_config)
                elif numeric_grade >= breakpoint_medium:
                    color = config.get_discord_grades_color_medium(user_config)
                else:
                    color = config.get_discord_grades_color_low(user_config)
            except (ValueError, AttributeError):
                color = config.get_discord_grades_color(user_config)

            content = f"**Nieuw cijfer: {grade_value}** voor {subject}"
            mention_role_id = config.get_discord_grades_mention_role_id(user_config)
            if mention_role_id:
                content += f" - <@&{mention_role_id}>"

            fields = [
                {"name": "Cijfer", "value": f"**{grade_value}**", "inline": True},
                {"name": "Vak", "value": f"{subject} - {subject_naam}", "inline": True},
                {
                    "name": "Periode",
                    "value": str(grade.get("periode", "?")),
                    "inline": True,
                },
            ]

            weging = grade.get("weging", 0)
            examen_weging = grade.get("examenWeging", 0)
            if weging or examen_weging:
                fields.append(
                    {
                        "name": "Weging",
                        "value": f"Voortgang: {weging}, examen: {examen_weging}",
                        "inline": True,
                    }
                )

            if grade.get("leerjaar"):
                fields.append(
                    {
                        "name": "Leerjaar",
                        "value": str(grade.get("leerjaar")),
                        "inline": True,
                    }
                )

            if grade.get("type"):
                fields.append(
                    {"name": "Type", "value": grade.get("type"), "inline": True}
                )

            if grade.get("herkansing"):
                herk_result = grade.get("herkansing", {}).get("resultaat", "?")
                fields.append(
                    {
                        "name": "Herkansbaar",
                        "value": f"type: {grade.get('herkansingstype', '?')}",
                        "inline": False,
                    }
                )

            flags = []
            if grade.get("teltNietmee"):
                flags.append("telt niet mee")
            if grade.get("vrijstelling"):
                flags.append("vrijstelling")
            if grade.get("toetsNietGemaakt"):
                flags.append("toets niet gemaakt")
            if grade.get("isExamendossierResultaat"):
                flags.append("examendossier")
            if grade.get("isVoortgangsdossierResultaat"):
                flags.append("voortgangsdossier")

            if flags:
                fields.append(
                    {"name": "Status", "value": "\n".join(flags), "inline": False}
                )

            if grade.get("datumInvoer"):
                fields.append(
                    {
                        "name": "Invoerdatum",
                        "value": grade.get("datumInvoer").split("T")[0],
                        "inline": True,
                    }
                )

            embed = {
                "title": f"Nieuw cijfer voor {display_name}",
                "description": f"**{subject}** - {test_name}",
                "color": color,
                "fields": fields,
                "footer": {"text": "SomPlus"},
            }

        elif change_type == "CHANGED":
            old_grade = change["old_grade"]
            new_grade = change["new_grade"]
            grade_changes = change.get("changes", {})

            subject = new_grade.get("vak", {}).get("afkorting", "")
            subject_naam = new_grade.get("vak", {}).get("naam", subject)
            test_name = new_grade.get("omschrijving", "Onbekend")

            changes_list = []
            color = config.get_discord_grades_color_medium(user_config)

            if "resultaat" in grade_changes:
                old_value = grade_changes["resultaat"]["old"]
                new_value = grade_changes["resultaat"]["new"]

                try:
                    old_numeric = float(str(old_value).replace(",", "."))
                    new_numeric = float(str(new_value).replace(",", "."))
                    diff = new_numeric - old_numeric

                    if old_numeric != 0:
                        pct_change = (diff / old_numeric) * 100
                        pct_str = f", {pct_change:+.1f}%"
                    else:
                        pct_str = ""

                    if new_numeric > old_numeric:
                        color = config.get_discord_grades_color_high(user_config)
                        changes_list.append(
                            f"**Cijfer**: ~~{old_value}~~ → **{new_value}** (+{diff:.1f}{pct_str})"
                        )
                    elif new_numeric < old_numeric:
                        color = config.get_discord_grades_color_low(user_config)
                        changes_list.append(
                            f"**Cijfer**: ~~{old_value}~~ → **{new_value}** ({diff:.1f}{pct_str})"
                        )
                    else:
                        changes_list.append(f"**Cijfer**: {old_value} → {new_value}")
                except (ValueError, AttributeError):
                    changes_list.append(
                        f"**Cijfer**: ~~{old_value}~~ → **{new_value}**"
                    )

            if "herkansing_resultaat" in grade_changes:
                old_herk = grade_changes["herkansing_resultaat"]["old"]
                new_herk = grade_changes["herkansing_resultaat"]["new"]

                try:
                    old_herk_num = float(str(old_herk).replace(",", "."))
                    new_herk_num = float(str(new_herk).replace(",", "."))
                    diff_herk = new_herk_num - old_herk_num

                    if old_herk_num != 0:
                        pct_change_herk = (diff_herk / old_herk_num) * 100
                        pct_str_herk = f", {pct_change_herk:+.1f}%"
                    else:
                        pct_str_herk = ""

                    if diff_herk != 0:
                        changes_list.append(
                            f"**Herkansing**: ~~{old_herk}~~ → **{new_herk}** ({diff_herk:+.1f}{pct_str_herk})"
                        )
                    else:
                        changes_list.append(
                            f"**Herkansing**: ~~{old_herk}~~ → **{new_herk}**"
                        )
                except (ValueError, AttributeError):
                    changes_list.append(
                        f"**Herkansing**: ~~{old_herk}~~ → **{new_herk}**"
                    )

            if "weging" in grade_changes:
                old_w = grade_changes["weging"]["old"]
                new_w = grade_changes["weging"]["new"]
                changes_list.append(f"**weging**: {old_w} → {new_w}")

            if "examenWeging" in grade_changes:
                old_ew = grade_changes["examenWeging"]["old"]
                new_ew = grade_changes["examenWeging"]["new"]
                changes_list.append(f"**examen weging**: {old_ew} → {new_ew}")

            if "teltNietmee" in grade_changes:
                old_t = grade_changes["teltNietmee"]["old"]
                new_t = grade_changes["teltNietmee"]["new"]
                old_str = "ja" if old_t else "nee"
                new_str = "ja" if new_t else "nee"
                changes_list.append(f"**telt niet mee**: {old_str} → {new_str}")

            if "vrijstelling" in grade_changes:
                old_v = grade_changes["vrijstelling"]["old"]
                new_v = grade_changes["vrijstelling"]["new"]
                old_str = "ja" if old_v else "nee"
                new_str = "ja" if new_v else "nee"
                changes_list.append(f"**vrijstelling**: {old_str} → {new_str}")

            if "periode" in grade_changes:
                old_p = grade_changes["periode"]["old"]
                new_p = grade_changes["periode"]["new"]
                changes_list.append(f"**periode**: {old_p} → {new_p}")

            content = f"**Cijfer gewijzigd** voor {subject}"
            mention_role_id = config.get_discord_grades_mention_role_id(user_config)
            if mention_role_id:
                content += f" - <@&{mention_role_id}>"

            fields = [
                {
                    "name": "Vak",
                    "value": f"{subject} - {subject_naam}",
                    "inline": False,
                },
                {
                    "name": "Wijzigingen",
                    "value": "\n".join(changes_list) if changes_list else "onbekend",
                    "inline": False,
                },
            ]

            current_grade = new_grade.get("geldendResultaat") or new_grade.get(
                "resultaat", "?"
            )
            fields.append(
                {
                    "name": "Huidig cijfer",
                    "value": f"**{current_grade}**",
                    "inline": True,
                }
            )

            if new_grade.get("periode"):
                fields.append(
                    {
                        "name": "Periode",
                        "value": str(new_grade.get("periode")),
                        "inline": True,
                    }
                )

            if new_grade.get("leerjaar"):
                fields.append(
                    {
                        "name": "Leerjaar",
                        "value": str(new_grade.get("leerjaar")),
                        "inline": True,
                    }
                )

            weging = new_grade.get("weging", 0)
            examen_weging = new_grade.get("examenWeging", 0)
            if weging or examen_weging:
                fields.append(
                    {
                        "name": "Weging",
                        "value": f"Voortgang: {weging}, examen: {examen_weging}",
                        "inline": False,
                    }
                )

            embed = {
                "title": f"Cijfer gewijzigd voor {display_name}",
                "description": f"**{subject}** - {test_name}",
                "color": color,
                "fields": fields,
                "footer": {"text": "SomPlus"},
            }

        elif change_type == "REMOVED":
            grade = change["grade"]
            grade_value = grade.get("geldendResultaat") or grade.get("resultaat", "")
            subject = grade.get("vak", {}).get("afkorting", "")
            subject_naam = grade.get("vak", {}).get("naam", subject)
            test_name = grade.get("omschrijving", "onbekend")

            color = config.get_discord_grades_color_low(user_config)
            content = f"**Cijfer verwijderd** voor {subject}: ~~{grade_value}~~"
            mention_role_id = config.get_discord_grades_mention_role_id(user_config)
            if mention_role_id:
                content += f" - <@&{mention_role_id}>"

            fields = [
                {
                    "name": "Verwijderd cijfer",
                    "value": f"~~{grade_value}~~",
                    "inline": True,
                },
                {"name": "Vak", "value": f"{subject} - {subject_naam}", "inline": True},
                {
                    "name": "Periode",
                    "value": str(grade.get("periode", "?")),
                    "inline": True,
                },
            ]

            weging = grade.get("weging", 0)
            examen_weging = grade.get("examenWeging", 0)
            if weging or examen_weging:
                fields.append(
                    {
                        "name": "Weging",
                        "value": f"Voortgang: {weging}, examen: {examen_weging}",
                        "inline": True,
                    }
                )

            if grade.get("type"):
                fields.append(
                    {"name": "Type", "value": grade.get("type"), "inline": True}
                )

            if grade.get("leerjaar"):
                fields.append(
                    {
                        "name": "Leerjaar",
                        "value": str(grade.get("leerjaar")),
                        "inline": True,
                    }
                )

            embed = {
                "title": f"Cijfer verwijderd voor {display_name}",
                "description": f"**{subject}** - {test_name}",
                "color": color,
                "fields": fields,
                "footer": {"text": "SomPlus"},
            }

        else:
            return

        payload = {
            "content": content,
            "tts": config.get_discord_grades_tts(user_config),
            "embeds": [embed],
        }

        webhook_url = config.get_discord_grades_webhook_url(user_config)
        self.send_webhook(webhook_url, payload)

    def send_schedule_notification(
        self, username, user_config, changes, current_schedule, rolled_over=False
    ):
        if not config.get_discord_schedule_enabled(user_config):
            return

        display_name = user_config["display_name"]
        change_count = len(changes)

        content = f"**{change_count} roosterwijziging{'en' if change_count != 1 else ''}** voor {display_name}"
        mention_role_id = config.get_discord_schedule_mention_role_id(user_config)
        if mention_role_id:
            content += f" | <@&{mention_role_id}>"

        changes_description = self.format_changes_detailed(changes)
        lessons_by_day = self.get_lessons_by_day(current_schedule)

        embeds = [
            {
                "title": "Roosterwijzigingen",
                "description": changes_description,
                "color": config.get_discord_schedule_color_changes(user_config),
                "footer": {"text": "SomPlus"},
            }
        ]

        today = datetime.now().weekday()

        if rolled_over:
            embeds.append(
                {
                    "title": "Volgende week",
                    "description": "Dit zijn wijzigingen voor volgende week.",
                    "color": config.get_discord_schedule_color_current(user_config),
                    "footer": {"text": "SomPlus"},
                }
            )
            affected_days = set(c["day"] for c in changes)
        else:
            if today in lessons_by_day:
                today_schedule = self.format_day_schedule(lessons_by_day[today])
                embeds.append(
                    {
                        "title": "Vandaag",
                        "description": today_schedule,
                        "color": config.get_discord_schedule_color_current(user_config),
                        "footer": {"text": "SomPlus"},
                    }
                )
            affected_days = set(c["day"] for c in changes if c["day"] > today)

        if affected_days:
            day_names = ["Ma", "Di", "Wo", "Do", "Vr"]
            for day in sorted(affected_days):
                if day in lessons_by_day and (rolled_over or day != today):
                    day_schedule = self.format_day_schedule(lessons_by_day[day])
                    embeds.append(
                        {
                            "title": f"{day_names[day]}",
                            "description": day_schedule,
                            "color": config.get_discord_schedule_color_current(
                                user_config
                            ),
                            "footer": {"text": "SomPlus"},
                        }
                    )

        payload = {
            "content": content,
            "tts": config.get_discord_schedule_tts(user_config),
            "embeds": embeds,
        }

        webhook_url = config.get_discord_schedule_webhook_url(user_config)
        self.send_webhook(webhook_url, payload)

    def send_error_notification(self, username, user_config, error_summary):
        if not config.get_discord_errors_enabled(user_config):
            return

        error_count = sum(len(errors) for errors in error_summary.values())

        embed = {
            "title": f"Fouten ({error_count})",
            "description": f"Er zijn {error_count} fout{'en' if error_count != 1 else ''} opgetreden in het afgelopen uur",
            "color": config.get_discord_errors_color(user_config),
            "footer": {"text": "SomPlus"},
        }

        payload = {
            "tts": config.get_discord_errors_tts(user_config),
            "embeds": [embed],
        }

        webhook_url = config.get_discord_errors_webhook_url(user_config)
        self.send_webhook(webhook_url, payload)

    def send_webhook(self, webhook_url, payload):
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.console_error(f"Discord webhook failed: {e}", indent=4)
            raise

    def format_changes_detailed(self, changes):
        day_names = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag"]
        lines = []

        for change in changes:
            day_name = day_names[change["day"]]

            if change["type"] == "UITVAL":
                lines.append(f"**{day_name}**: uitval **{change['subject']}**")
            elif change["type"] == "COMPLETE_UITVAL":
                count = change.get("count", "?")
                lines.append(
                    f"**{day_name}**: complete uitval **{change['subject']}** ({count} lessen)"
                )
            elif change["type"] == "GEDEELTELIJKE_UITVAL":
                count = change.get("count", 1)
                lines.append(
                    f"**{day_name}**: gedeeltelijke uitval **{change['subject']}** (-{count} les{'sen' if count > 1 else ''})"
                )
            elif change["type"] == "ANTI_UITVAL":
                count = change.get("count", 1)
                lines.append(
                    f"**{day_name}**: extra les **{change['subject']}** (+{count})"
                )
            elif change["type"] == "SUBJECT_CHANGE":
                period = change.get("period", "?")
                lines.append(
                    f"**{day_name}** {period}e uur: **{change['old']}** -> **{change['new']}**"
                )
            elif change["type"] == "TEACHER_CHANGE":
                period = change.get("period", "?")
                lines.append(
                    f"**{day_name}** {period}e uur **{change['subject']}**: docent {change['old']} -> {change['new']}"
                )
            elif change["type"] == "LOCATION_CHANGE":
                period = change.get("period", "?")
                lines.append(
                    f"**{day_name}** {period}e uur **{change['subject']}**: lokaal {change['old']} -> {change['new']}"
                )

        return "\n".join(lines) if lines else "Geen wijzigingen"

    def get_lessons_by_day(self, schedule_data):
        lessons_by_day = {}
        if schedule_data and "lessons" in schedule_data:
            for lesson in schedule_data["lessons"]:
                day = lesson["day"]
                if day not in lessons_by_day:
                    lessons_by_day[day] = []
                lessons_by_day[day].append(lesson)
        return lessons_by_day

    def format_day_schedule(self, lessons):
        if not lessons:
            return "Geen lessen"

        lessons.sort(key=lambda x: x["period"])

        lines = []
        for lesson in lessons:
            if lesson["subject"]:
                lines.append(f"{lesson['period']}e: {lesson['subject']}")

        return "\n".join(lines) if lines else "Geen lessen"
