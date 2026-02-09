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

            additional = entry.get("additionalObjects", {})
            subject_name = additional.get("vaknaam", "")
            if subject_name in filters["exclude_subjects"]:
                continue

            clean_entry = {}
            for k, v in entry.items():
                if k in ["links", "permissions", "$type"]:
                    continue
                clean_entry[k] = v

            grades.append(clean_entry)

        grades.sort(
            key=lambda x: x.get("datumInvoerEerstePoging", ""),
            reverse=True,
        )

        return grades

    def has_valid_result(self, entry):
        has_cijfer = entry.get("cijfer") is not None
        has_formatted = entry.get("formattedResultaat") not in [None, ""]
        has_label = entry.get("label") not in [None, ""]
        return has_cijfer or has_formatted or has_label

    def load_cached_data(self):
        path = self.get_user_data_path("grades.json")
        return self.load_json_file(path)

    def save_data(self, data):
        path = self.get_user_data_path("grades.json")
        self.save_json_file(path, data)

    def compare_data(self, old_data, new_data):
        def make_key(grade):
            additional = grade.get("additionalObjects", {})
            subject = additional.get("vaknaam", "")
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

                old_result = old_grade.get("formattedResultaat", "")
                new_result = new_grade.get("formattedResultaat", "")
                if old_result != new_result:
                    grade_changes["resultaat"] = {"old": old_result, "new": new_result}

                old_has_herkansing = old_grade.get("cijferHerkansing1") is not None
                new_has_herkansing = new_grade.get("cijferHerkansing1") is not None

                if new_has_herkansing and not old_has_herkansing:
                    changes.append(
                        {
                            "type": "NEW_HERKANSING",
                            "grade": new_grade,
                            "original_result": old_grade.get("formattedEerstePoging", ""),
                            "herkansing_result": new_grade.get("formattedHerkansing1", ""),
                        }
                    )
                elif new_has_herkansing and old_has_herkansing:
                    old_herk_result = old_grade.get("formattedHerkansing1", "")
                    new_herk_result = new_grade.get("formattedHerkansing1", "")
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
                grade = change.get("new_grade") or change.get("grade")
            else:
                grade = change.get("grade")
            return grade.get("datumInvoerEerstePoging", "")

        changes.sort(key=get_datetime, reverse=True)

        return changes

    def notify_changes(self, changes, notifiers):
        for grade in changes:
            for notifier in notifiers:
                notifier.send_grade_notification(self.username, self.user_config, grade)
