from datetime import datetime, timedelta
from collections import Counter
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
    api_url = data.get("somtoday_api_url", "https://api.somtoday.nl")

    return btoken, api_url


def grades_main(btoken, api_url):
    lln_id = "???"  # Not your studentnumber (leerlingnummer) but the long id you get via /rest/v1/account/

    url = f"{api_url}/rest/v1/resultaten/huidigVoorLeerling/{lln_id}"

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

    # Removing unwanted columntypes and subjects
    remove_items = []
    subjects_to_remove = ["4a-in", "LOB", "MEN"]  # Change to all the subjects you don't need (usually subjects you don't get grades from), so things don't bug 
    for item in data:
        item_type = item["type"]
        item_name = item["vak"]["afkorting"]

        if item_type != "Toetskolom" or item_name in subjects_to_remove: # The types are usually "Toetskolom", "PeriodeGemiddeldeKolom", "RapportGemiddeldeKolom" and "SEGemiddeldeKolom". I only use toetskolom since I'm using grades from tests. See the README for more info
            remove_items.append(item)
        else:
            # Removing items with no results
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


def schedule_notification_generator(oldScheduleData, newScheduleData):
    changes = []
    schedulesChangedDays = []
    weekdays = {
        0: "MO",
        1: "TU",
        2: "WE",
        3: "TH",
        4: "FR",
        5: "SA",
        6: "SU"
    }
    for day in range(5):
        dayChanges = []
        dayScheduleOldLessonsOnly = []
        dayScheduleNewLessonsOnly = []
        for hour in range(9):
            dayScheduleOldLessonsOnly.append(oldScheduleData[hour][day].split(" - ")[0])
            dayScheduleNewLessonsOnly.append(newScheduleData[hour][day].split(" - ")[0])
        counter1 = Counter(dayScheduleOldLessonsOnly)
        counter2 = Counter(dayScheduleNewLessonsOnly)

        totalHoursCanceled = 0

        allLessonsOccurringThatDay = set(dayScheduleOldLessonsOnly).union(set(dayScheduleNewLessonsOnly))

        for item in allLessonsOccurringThatDay:
            if item.strip() == "":
                continue

            oldCount = counter1[item]
            newCount = counter2[item]

            canceledHours = oldCount - newCount

            totalHoursCanceled += abs(canceledHours)

            if canceledHours == 1:
                if oldCount == 1:
                    # 1 hour in the old schedule that has been canceled
                    dayChanges.append(f"{weekdays[day]}: Cancellation {item}")
                if oldCount > 1:
                    # A mltiple lessons in the old schedule AND only 1 has been canceled
                    dayChanges.append(f"{weekdays[day]}: PARTIAL cancellation {item}")
            if canceledHours > 1:
                if newCount == 0:
                    # Multiple hours in the old schedule, and all of them are canceled
                    dayChanges.append(f"{weekdays[day]}: COMPLETE cancellation {item}")
                else:
                    # If multiple but NOT ALL hours are canceled
                    # Practically never happens (could only happen if you have 3 or more lessons of 1 subject on 1 day and multiple but not all of them are cancelled)
                    dayChanges.append(f"{weekdays[day]}: {canceledHours} TIMES cancellation {item}")

            if canceledHours < 0:
                # Anti-cancellation, so hours put back or added
                if canceledHours == -1:
                    dayChanges.append(f"{weekdays[day]}: ANTI-CANCELLATION!!! {item}")
                    pass
                if canceledHours < -1:
                    dayChanges.append(f"{weekdays[day]}: {abs(canceledHours)} HOURS ANTI-CANCELLATION???!!! {item}")
                    pass


        for lesson in range(9):
            timeStr = f"{weekdays[day]} {lesson + 1}th"
            oldCell = oldScheduleData[lesson][day]
            newCell = newScheduleData[lesson][day]

            try:
                oldSubject, oldTeacher, oldRoom = oldCell.split(" - ")
            except ValueError:
                oldSubject = "Empty"
                oldTeacher = "Empty"
                oldRoom = "Empty"
            if oldSubject.strip() == "":
                oldSubject = "Empty"
            if oldTeacher.strip() == "":
                oldTeacher = "Empty"
            if oldRoom.strip() == "":
                oldRoom = "Empty"

            try:
                newSubject, newTeacher, newRoom = newCell.split(" - ")
            except ValueError:
                newSubject = "Empty"
                newTeacher = "Empty"
                newRoom = "Empty"
            if newSubject.strip() == "":
                newSubject = "Empty"
            if newTeacher.strip() == "":
                newTeacher = "Empty"
            if newRoom.strip() == "":
                newRoom = "Empty"

            if oldSubject != newSubject:
                dayChanges.append(f"{timeStr}: {oldSubject} -> {newSubject}")
            else:
                if oldTeacher != newTeacher:
                    dayChanges.append(f"{timeStr}: {oldTeacher} -> {newTeacher}")
                if oldRoom != newRoom:
                    dayChanges.append(f"{timeStr}: {oldRoom} -> {newRoom}")

        if totalHoursCanceled != 0:
            changedScheduleDay = f"SCHEDULE {weekdays[day]}: "
            i = 1
            for item in dayScheduleNewLessonsOnly:
                if item == "":
                    item = "Empty"

                if changedScheduleDay == f"SCHEDULE {weekdays[day]}: ":
                    changedScheduleDay += str(i) + "th = " + item
                else:
                    changedScheduleDay += " | " + str(i) + "th = " + item
                i += 1
            schedulesChangedDays.append(changedScheduleDay)

        for item in dayChanges:
            changes.append(item)

    changesStr = ""

    canceledItems = [item for item in changes if "cancellation" in item.lower()]
    nonCanceledItems = [item for item in changes if "cancellation" not in item.lower()]

    changes = canceledItems + nonCanceledItems

    for item in changes:
        if changesStr != "":
            changesStr += " | " + item
        else:
            changesStr += item

    scheduleStr = ""
    for item in schedulesChangedDays:
        if scheduleStr != "":
            scheduleStr += " // " + item
        else:
            scheduleStr += item

    return changesStr, scheduleStr


def schedule_main(btoken, api_url):
    today = datetime.now(pytz.timezone("Europe/Amsterdam"))
    current_hour = int(today.strftime("%H"))
    weekday = today.weekday()
    days_since_monday = weekday
    if weekday == 0:  # I have no idea why I put this here, but I feel everything will break if I remove it
        days_since_monday = 0
    if weekday >= 5 or (weekday == 4 and current_hour >= 16):  # Every friday at 16:00, it starts working with the schedule for the next week
        days_since_monday -= 7 
    monday = today - timedelta(days=days_since_monday)
    saturday = monday + timedelta(days=5)
    monday_format = monday.strftime("%Y-%m-%d")
    saturday_format = saturday.strftime("%Y-%m-%d")
    new_week_number = monday.strftime("%W")

    url = f"{api_url}/rest/v1/afspraken?sort=asc-id&additional=vak&additional=docentAfkortingen&additional=leerlingen&begindatum={monday_format}&einddatum={saturday_format}"

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
                lesson_info = item["titel"].split(" - ")[1]
                subject_abbr = ""
                subjects_in_schedule = ['BIOL', 'CKV', 'ENTL', 'FATL', 'LO', 'MAAT', 'MEN', 'NAT', 'NLT', 'NETL', 'SCHK', 'WISB']  # Change to all the subjects you want in your schedule
                for afk in subjects_in_schedule:
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

def main():
    btoken, api_url = refresh_tokens()
    grades_main(btoken, api_url)
    schedule_main(btoken, api_url)
    
if __name__ == "__main__":
    main()
    print("Completed!")
