from datetime import datetime
import requests
import pickle


# Choose a week (probably in the (far) future) were your schedule has no changes

starting_date = "2024-12-09" # from (monday)
end_date = "2024-12-14" # to (saturday)

url = f"https://api.somtoday.nl/rest/v1/afspraken?sort=asc-id&additional=vak&additional=docentAfkortingen&additional=leerlingen&begindatum={starting_date}&einddatum={end_date}"

btoken = ""

headers = {
    "Authorization": f"Bearer {btoken}",
    "Accept": "application/json"
}

response = requests.get(url, headers = headers)
data = response.json()


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


with open("standard_schedule.pkl", "wb") as file:
    pickle.dump(schedule_data, file)

print("Completed.")
