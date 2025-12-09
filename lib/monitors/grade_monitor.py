from lib.monitors.base_monitor import BaseMonitor
from lib.utils import config


class GradeMonitor(BaseMonitor):
    def is_enabled(self):
        return config.get_grades_enabled(self.user_config)

    def fetch_data(self, access_token):
        leerling_id = self.user_config["auth"]["leerling_id"]
        return self.api.fetch_grades(access_token, leerling_id)

    def process_data(self, raw_data):
        filters = config.get_grades_filters(self.user_config)
        grades = []

        for entry in raw_data:
            if not isinstance(entry, dict):
                continue

            if not self.has_valid_result(entry):
                continue

            entry_type = entry.get("type", "")
            if entry_type in filters["exclude_types"]:
                continue

            vak = entry.get("vak", {})
            if not isinstance(vak, dict):
                vak = {}
            subject_abbr = vak.get("afkorting", "")
            if subject_abbr in filters["exclude_subjects"]:
                continue

            clean_entry = {}
            for k, v in entry.items():
                if k in ["links", "permissions", "$type"]:
                    continue
                if k == "additionalObjects" and (not v or v == {}):
                    continue
                clean_entry[k] = v

            if "vak" in clean_entry and isinstance(clean_entry["vak"], dict):
                cleaned_vak = {}
                for k, v in clean_entry["vak"].items():
                    if k in ["links", "permissions"]:
                        continue
                    if k == "additionalObjects" and (not v or v == {}):
                        continue
                    cleaned_vak[k] = v
                clean_entry["vak"] = cleaned_vak

            if "leerling" in clean_entry and isinstance(clean_entry["leerling"], dict):
                cleaned_leerling = {}
                for k, v in clean_entry["leerling"].items():
                    if k in ["links", "permissions"]:
                        continue
                    if k == "additionalObjects" and (not v or v == {}):
                        continue
                    cleaned_leerling[k] = v
                clean_entry["leerling"] = cleaned_leerling

            if "herkansing" in clean_entry and isinstance(
                clean_entry["herkansing"], dict
            ):
                cleaned_herkansing = {}
                for k, v in clean_entry["herkansing"].items():
                    if k in ["links", "permissions"]:
                        continue
                    if k == "additionalObjects" and (not v or v == {}):
                        continue
                    cleaned_herkansing[k] = v
                clean_entry["herkansing"] = cleaned_herkansing

            grades.append(clean_entry)

        grades.sort(
            key=lambda x: x.get("datumInvoer", ""),
            reverse=True,
        )

        return grades

    def has_valid_result(self, entry):
        has_result = entry.get("resultaat") not in [None, ""]
        has_label = entry.get("resultaatLabelAfkorting") not in [None, ""]
        return has_result or has_label

    def load_cached_data(self):
        path = self.get_user_data_path("grades.json")
        return self.load_json_file(path)

    def save_data(self, data):
        path = self.get_user_data_path("grades.json")
        self.save_json_file(path, data)

    def compare_data(self, old_data, new_data):
        def make_key(grade):
            subject = grade.get("vak", {}).get("afkorting", "")
            test = grade.get("omschrijving", "")
            return (subject, test)

        old_dict = {make_key(g): g for g in old_data}
        new_dict = {make_key(g): g for g in new_data}

        changes = []

        for key, grade in new_dict.items():
            if key not in old_dict:
                changes.append({"type": "NEW", "grade": grade})

        for key, new_grade in new_dict.items():
            if key in old_dict:
                old_grade = old_dict[key]
                grade_changes = {}

                old_result = old_grade.get("geldendResultaat") or old_grade.get(
                    "resultaat", ""
                )
                new_result = new_grade.get("geldendResultaat") or new_grade.get(
                    "resultaat", ""
                )
                if old_result != new_result:
                    grade_changes["resultaat"] = {"old": old_result, "new": new_result}

                old_has_herkansing = "herkansing" in old_grade and old_grade.get(
                    "herkansing"
                )
                new_has_herkansing = "herkansing" in new_grade and new_grade.get(
                    "herkansing"
                )

                if new_has_herkansing and not old_has_herkansing:
                    changes.append(
                        {
                            "type": "NEW_HERKANSING",
                            "grade": new_grade,
                            "original_result": old_result,
                            "herkansing_result": new_grade.get("herkansing", {}).get(
                                "resultaat", ""
                            ),
                        }
                    )
                elif new_has_herkansing and old_has_herkansing:
                    old_herk_result = old_grade.get("herkansing", {}).get(
                        "resultaat", ""
                    )
                    new_herk_result = new_grade.get("herkansing", {}).get(
                        "resultaat", ""
                    )
                    if old_herk_result != new_herk_result:
                        grade_changes["herkansing_resultaat"] = {
                            "old": old_herk_result,
                            "new": new_herk_result,
                        }

                if old_grade.get("weging") != new_grade.get("weging"):
                    grade_changes["weging"] = {
                        "old": old_grade.get("weging"),
                        "new": new_grade.get("weging"),
                    }

                if old_grade.get("examenWeging") != new_grade.get("examenWeging"):
                    grade_changes["examenWeging"] = {
                        "old": old_grade.get("examenWeging"),
                        "new": new_grade.get("examenWeging"),
                    }

                if old_grade.get("teltNietmee") != new_grade.get("teltNietmee"):
                    grade_changes["teltNietmee"] = {
                        "old": old_grade.get("teltNietmee"),
                        "new": new_grade.get("teltNietmee"),
                    }

                if old_grade.get("vrijstelling") != new_grade.get("vrijstelling"):
                    grade_changes["vrijstelling"] = {
                        "old": old_grade.get("vrijstelling"),
                        "new": new_grade.get("vrijstelling"),
                    }

                if old_grade.get("periode") != new_grade.get("periode"):
                    grade_changes["periode"] = {
                        "old": old_grade.get("periode"),
                        "new": new_grade.get("periode"),
                    }

                if grade_changes:
                    changes.append(
                        {
                            "type": "CHANGED",
                            "old_grade": old_grade,
                            "new_grade": new_grade,
                            "changes": grade_changes,
                        }
                    )

        for key, grade in old_dict.items():
            if key not in new_dict:
                changes.append({"type": "REMOVED", "grade": grade})

        def get_datetime(change):
            if change["type"] in ["CHANGED", "NEW_HERKANSING"]:
                dt_str = (
                    change["new_grade"].get("datumInvoer", "")
                    if "new_grade" in change
                    else change["grade"].get("datumInvoer", "")
                )
            else:
                dt_str = change["grade"].get("datumInvoer", "")
            return dt_str

        changes.sort(key=get_datetime, reverse=True)

        return changes

    def notify_changes(self, changes, notifiers):
        for grade in changes:
            for notifier in notifiers:
                notifier.send_grade_notification(self.username, self.user_config, grade)
