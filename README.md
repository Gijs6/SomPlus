# SomPlus

SomPlus allows you to be notified by changes in grades and schedule through the [Somtoday API](https://github.com/elisaado/somtoday-api-docs).

It relies on the files `refreshtoken.txt`, `gradelist.pkl`, `schedule.pkl`, `week_number.txt`, and `standard_schedule.pkl`. You can replace the `.pkl` files with `.json` files if you prefer that.

The auth for the Som API is a huge mess. To get the refreshtoken, I use the [Somtoday SSO tool](https://github.com/m-caeliusrufus/Somtoday-SSO-tool) (in python), and store the token in `refreshtoken.txt`. You can also use [SomtodaySSOLogin](https://github.com/Underlyingglitch/SomtodaySSOLogin) (in js) to get the token.

The schedule section only uses items with a defined starting hour. Any items that do not align with standard lesson times are excluded. You could save all the times directly from the data, but the notification generator won't work then.

## Configuration

To make the script work, you will need to adjust the following things. These will differ across schools:

1. **`lln_id` in `grades_main`**  
   This is not the "leerlingnummer" but the ID you get via `/rest/v1/account/`.

2. **Removing the column types in `grades_main`**  
   You can find all the column types in the raw data from `/rest/v1/resultaten/huidigVoorLeerling/...`. Usually, the `toetskolom` is needed if you're working with grades from tests. If you're working with period or report grades, you will need either the `PeriodeGemiddeldeKolom` or `RapportGemiddeldeKolom`. On most schools one of them is rounded and the other is not (I think), but it differs, so just look wich one does the thing you want :D

3. **`subjects_to_remove` in `grades_main`**  

4. **`maximum_amount_lessons` in `schedule_notification_generator`, `schedule_main`, and `saveStandardSchedule.py`**  

5. **`subjects_in_schedule` in `schedule_main`**  

6. **`btoken` in `saveStandardSchedule.py`**  
   You only need to save a new standard schedule if you have a new one, so you can just generate a extra token when you need to run this script

## Instructions for Getting the Auth JSON for the Sheet Updater

The Sheet Updater is quite inefficient and very specific, but you may find it helpful.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or use an existing one)
2. Enable the **Google Sheets API** and **Google Drive API** under **APIs & Services > Library**
3. Create a **Service Account** by going to **APIs & Services > Credentials > Create Credentials** and add at least editor permissions
4. On the service account page, create a key and download the JSON file
5. Share your spreadsheet with the service account email (found on the service account page) and give editor permissions
