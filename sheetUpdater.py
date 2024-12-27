from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from collections import defaultdict
import requests
import re


def get_grade_data(api_url, btoken, column):
    student_id = "???"  # Not your student number (leerlingnummer), but the long ID you get via /rest/v1/account/

    url = f"{api_url}/rest/v1/resultaten/huidigVoorLeerling/{student_id}"

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

    # Removing unwanted column types and subjects
    remove_items = []
    subjects_to_remove = ["4a-in", "LOB", "MEN"]  # Modify with subjects you don't need (usually subjects with no grades)
    for item in data:
        item_type = item["type"]
        item_name = item["vak"]["afkorting"]

        if item_type != column or item_name in subjects_to_remove:  # The types are usually "Toetskolom", "PeriodeGemiddeldeKolom", "RapportGemiddeldeKolom" and "SEGemiddeldeKolom". I only use toetskolom since I'm using grades from tests. See the README for more info
            remove_items.append(item)
        else:
            # Removing items without results
            try:
                result = item["geldendResultaat"]
            except KeyError:
                try:
                    result = item["resultaatLabelAfkorting"]
                except:
                    remove_items.append(item)

    for item in remove_items:
        data.remove(item)

    # Sorting data by the date it was entered
    data = sorted(data, key=lambda x: datetime.strptime(x["datumInvoer"], "%Y-%m-%dT%H:%M:%S.%f%z"), reverse=True)

    return data


def auth_and_initialize(auth_json_path):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(auth_json_path, scope)

    return gspread.authorize(credentials)


def update_grade_list_sheet(api_url, btoken, gc):
    data = get_grade_data(api_url, btoken, "RapportGemiddeldeKolom")  # Change to "PeriodeGemiddeldeKolom" if the grades are not rounded correctly

    spreadsheet = gc.open("Grade list")  # Change to your sheet's name
    worksheet = spreadsheet.get_worksheet(0)

    period_data = defaultdict(list)

    num_periods = 4

    for item in data:
        try:
            result = item["geldendResultaat"]
            result = float(result.replace(",", "."))
        except:
            try:
                result = item["resultaatLabelAfkorting"]
            except:
                result = ""
        subject = item["vak"]["afkorting"]
        period = item["periode"]

        append_data = {
            "result": result,
            "subject": subject,
            "period": period
        }

        if 1 <= period <= num_periods:
            period_data[period].append(append_data)
        else:
            raise KeyError("Result does not belong to any period")

    order = ["BIOL", "CKV", "ENTL", "FATL", "MAAT", "NAT", "NLT", "NETL", "SCHK", "WISB"]

    period_form = {period: [] for period in range(1, (num_periods + 1))}

    for period, period_list in period_data.items():
        sorted_list = sorted(period_list, key=lambda x: order.index(x["subject"]))
        period_form[period] = [[item["result"]] for item in sorted_list]

    first_cell = "B2"  # Top-left cell, starting point of the range
    num_subjects = len(order)

    column_str, row_str = re.match(r"([A-Z]+)([0-9]+)", first_cell).groups()
    first_cell_column_number = sum((ord(char) - 64) * (26 ** i) for i, char in enumerate(reversed(column_str)))
    first_cell_row_number = int(row_str)

    ranges = {}

    for period in range(1, (num_periods + 1)):
        column_num = first_cell_column_number + (num_periods - 1)
        column_letter = ""
        while column_num > 0:
            column_num, remainder = divmod(column_num - 1, 26)
            column_letter = chr(65 + remainder) + column_letter
        start_row = first_cell_row_number
        end_row = first_cell_row_number + (num_subjects - 1)
        ranges[period] = f"{column_letter}{start_row}:{column_letter}{end_row}"

    # DEBUG
    print(ranges)

    for period, range_name in ranges.items():
        worksheet.update(range_name=range_name, values=period_form[period])


def update_test_list_sheet(api_url, btoken, gc):
    data = get_grade_data(api_url, btoken, "Toetskolom")
    sheet = gc.open("Test list")  # Change to your sheet's name
    worksheet = sheet.get_worksheet(0)

    column_values = worksheet.col_values(6)

    for item in data:
        test_title = item["toetsnaam"]
        grade = item["resultaat"]
        input_date = item["invoerdatumtijd"]

        for i, cell_value in enumerate(column_values):
            if cell_value == test_title:
                row_number = i + 1
                worksheet.update_cell(row_number, 1, grade)  # Result in column A
                worksheet.update_cell(row_number, 2, input_date)  # Date in column B
                break


if __name__ == "__main__":
    somtoday_api_url = "https://api.somtoday.nl"  # This could be different across schools
    btoken = "abcdefg"
    auth_json_path = "auth.json"
    gc = auth_and_initialize(auth_json_path)
    update_grade_list_sheet(somtoday_api_url, btoken, gc)
    update_test_list_sheet(somtoday_api_url, btoken, gc)
