from datetime import datetime, timedelta
import pickle
import pytz
import requests


def refresh_tokens():
    with open("refreshtoken.txt", "r") as file:
        rtoken1 = file.read()
    url = "https://somtoday.nl/oauth2/token"
    body = {
        "grant_type": "refresh_token",
        "refresh_token": rtoken1,
        "client_id": "D50E0C06-32D1-4B41-A137-A9A850C892C2"
    }
    response = requests.post(url, data=body)

    data = response.json()

    with open("refresh_token.txt", "w") as file:
        file.write(data.get("refresh_token", rtoken1))

    btoken = data.get("access_token")

    return btoken


def grades_main(btoken):
    lln_id = "???"

    url = f"https://api.somtoday.nl/rest/v1/resultaten/huidigVoorLeerling/{lln_id}"

    headers = {
        "Authorization": f"Bearer {btoken}",
        "Accept": "application/json",
        "Origin": "https://somtoday.nl",
        "Range": "items=0-1000"
    }

    data = []

    response = requests.get(url, headers=headers)
    response_data = response.json()
    for item in response_data["items"]:
        data.append(item)

    # Removing unwanted subjects
    remove_items = []
    types_to_remove = ["PeriodeGemiddeldeKolom", "RapportGemiddeldeKolom", "SEGemiddeldeKolom"]
    subjects_to_remove = ["4a-in", "LOB", "MEN"]

    for item in data:
        item_type = item["type"]
        item_name = item["vak"]["afkorting"]

        if item_type in types_to_remove or item_name in subjects_to_remove:
            remove_items.append(item)
        else:
            # Removing items with no grades/results
            try:
                result = item["geldendResultaat"]
            except KeyError:
                try:
                    result = item["resultaatLabelAfkorting"]
                except:
                    remove_items.append(item)

    for item in remove_items:
        data.remove(item)

    data = sorted(data, key=lambda x: datetime.strptime(x["datumInvoer"], "%Y-%m-%dT%H:%M:%S.%f%z"), reverse=True)

    new_grade_list = []

    for grade in data:
        try:
            result = grade["geldendResultaat"]
        except KeyError:
            # For grades with a letter as result
            result = grade["resultaatLabelAfkorting"]
        input_datetime = datetime.strptime(grade["datumInvoer"], "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
            "%d/%m/%Y %H:%M:%S")
        subject_abbr = grade["vak"]["afkorting"]
        subject_full = grade["vak"]["naam"]
        title = grade["omschrijving"]
        weighting = grade["weging"]
        new_grade_list.append({
            "result": result,
            "inputdatetime": input_datetime,
            "subjectabbr": subject_abbr,
            "subject_full": subject_full,
            "title": title,
            "weighting": weighting
        })

    with open("gradelist.pkl", "rb") as file:
        old_grade_list = pickle.load(file)

    with open("gradelist.pkl", "wb") as file:
        pickle.dump(new_grade_list, file)

    if old_grade_list != new_grade_list:
        # Send notification

        # Example Discord webhook notification
        latest_grade = new_grade_list[0]["subject_full"]

        data = {
            "content": f"New grade for {latest_grade} | @everyone️",
            "components": [],
            "actions": {}
        }
        requests.post(
            "https://discord.com/api/webhooks/...", json=data)


def schedule_notification_generator(old_schedule, new_schedule):
    changes = []

    week_day_names = {
        0: "MA",
        1: "DI",
        2: "WO",
        3: "DO",
        4: "VR",
        5: "ZA",
        6: "ZO"
    }

    maximum_amount_lessons = 9  # Change to adjust the number of maximum lessons on a day

    for day in range(5):  # Change to adjust the number of days
        changes_this_day = []
        schedule_this_day_old_only_lessons = []
        schedule_this_day_new_only_lessons = []
        for hour in range(maximum_amount_lessons):
            schedule_this_day_old_only_lessons.append(old_schedule[hour][day].split(" - ")[0])
            schedule_this_day_new_only_lessons.append(new_schedule[hour][day].split(" - ")[0])
        set_old = set(schedule_this_day_old_only_lessons)
        set_new = set(schedule_this_day_new_only_lessons)
        lessons_canceled = list(set_old - set_new)
        for subject in lessons_canceled:
            changes_this_day.append(f"{week_day_names[day]}: Uitval {subject}! ")

        for lesson in range(maximum_amount_lessons):
            time_info = f"{week_day_names[day]} {lesson + 1}e"
            old_lesson_info = old_schedule[lesson][day]
            new_lesson_info = new_schedule[lesson][day]

            try:
                old_subject, old_teacher, old_classroom = old_lesson_info.split(" - ")
            except ValueError:
                old_subject = "Nothing"
                old_teacher = "Nothing"
                old_classroom = "Nothing"
            if old_subject.strip() == "":
                old_subject = "Nothing"
            if old_teacher.strip() == "":
                old_teacher = "Nothing"
            if old_classroom.strip() == "":
                old_classroom = "Nothing"

            try:
                new_subject, new_teacher, new_classroom = new_lesson_info.split(" - ")
            except ValueError:
                new_subject = "Nothing"
                new_teacher = "Nothing"
                new_classroom = "Nothing"
            if new_subject.strip() == "":
                new_subject = "Nothing"
            if new_teacher.strip() == "":
                new_teacher = "Nothing"
            if new_classroom.strip() == "":
                new_classroom = "Nothing"

            if old_subject != new_subject:
                changes_this_day.append(f"{time_info}: {old_subject} -> {new_subject}")
            else:
                if old_teacher != new_teacher:
                    changes_this_day.append(f"{time_info}: {old_teacher} -> {new_teacher}")
                if old_classroom != new_classroom:
                    changes_this_day.append(f"{time_info}: {old_classroom} -> {new_classroom}")

        for item in changes_this_day:
            changes.append(item)

    changes_notification = ""

    cancelled_items = [item for item in changes if "Uitval" in item]
    non_cancelled_items = [item for item in changes if "Uitval" not in item]

    # This is to make sure the cancelled items are at the beginning of the notification
    changes = cancelled_items + non_cancelled_items

    for item in changes:
        if changes_notification != "":
            changes_notification += " | " + item
        else:
            changes_notification += item

    return changes_notification


def schedule_main(btoken):
    today = datetime.now(pytz.timezone("Europe/Amsterdam"))
    current_hour = int(today.strftime("%H"))
    weekday = today.weekday()
    days_since_monday = weekday
    if weekday == 0:  # I have no idea why I put this here, but I feel everything will break if I remove it
        days_since_monday = 0
    if weekday >= 5 or (
            weekday == 4 and current_hour >= 16):  # Every friday at 16:00, it starts working with the schedule for the next week
        days_since_monday -= 7
    monday = today - timedelta(days=days_since_monday)
    saturday = monday + timedelta(days=5)
    monday_format = monday.strftime("%Y-%m-%d")
    saturday_format = saturday.strftime("%Y-%m-%d")
    new_week_number = monday.strftime("%W")

    url = f"https://api.somtoday.nl/rest/v1/afspraken?sort=asc-id&additional=vak&additional=docentAfkortingen&additional=leerlingen&begindatum={monday_format}&einddatum={saturday_format}"

    headers = {
        "Authorization": f"Bearer {btoken}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    data = sorted(data["items"], key=lambda x: datetime.strptime(x["beginDatumTijd"], "%Y-%m-%dT%H:%M:%S.%f%z"))

    lessons_to_remove = []

    for item in data:
        try:
            # Removing every item that has no starting hour, otherwise things will break
            test_thing = item["beginLesuur"]
        except KeyError:
            lessons_to_remove.append(item)

    for item in lessons_to_remove:
        data.remove(item)

    maximum_amount_lessons = 9  # Change to adjust the number of maximum lessons on a day

    schedule_data = [["" for _ in range(5)] for _ in range(maximum_amount_lessons)]


    for item in data:
        start_hour = item["beginLesuur"]
        end_hour = item["eindLesuur"]
        try:
            subject_abbr = item["additionalObjects"]["vak"]["afkorting"]
        except:
            try:
                # Sometimes item["additionalObjects"]["vak"]["afkorting"] will be empty, so it checks if any subject title is in the description of the lesson
                lesson_info = item["titel"]
                subject_abbr = ""
                b = ['BIOL', 'CKV', 'ENTL', 'FATL', 'LO', 'MAAT', 'MEN', 'NAT', 'NLT', 'NETL', 'SCHK',
                     'WISB']  # Change to all the subjects you want in your schedule
                for afk in b:
                    if afk in lesson_info:
                        subject_abbr = afk
                if subject_abbr == "":
                    subject_abbr = "N/A"
            except:
                subject_abbr = "N/A"
        teacher = item["additionalObjects"]["docentAfkortingen"].upper()
        classroom = item["locatie"]
        starting_datetime = datetime.strptime(item["beginDatumTijd"][:19], "%Y-%m-%dT%H:%M:%S")
        day_index = starting_datetime.weekday()
        for lesson_hour in range(start_hour, end_hour + 1):
            schedule_data[lesson_hour - 1][day_index] = f"{subject_abbr} - {teacher} - {classroom}"

    new_schedule = schedule_data

    with open("schedule.pkl", "rb") as file:
        old_schedule = pickle.load(file)

    with open("schedule.pkl", "wb") as file:
        pickle.dump(new_schedule, file)

    with open("week_number.txt", "r") as file:
        old_week_number = file.read()

    with open("week_number.txt", "w") as file:
        file.write(new_week_number)

    if old_week_number != new_week_number:
        # If there is a new week, it doesn't check with the old schedule, but with the standard schedule, see other file for making standard schedule
        with open("standard_schedule.pkl", "rb") as file:
            old_schedule = pickle.load(file)

    if old_schedule != new_schedule:
        schedule_notification_data = schedule_notification_generator(old_schedule, new_schedule)

        # Code for sending notification


try:
    btoken = refresh_tokens()

    try:
        grades_main(btoken)
    except Exception as e:
        print("Error with grades", e)

    try:
        schedule_main(btoken)
    except Exception as e:
        print("Error with schedule", e)


except Exception as e:
    print("Error with token", e)

print("Completed :D")
