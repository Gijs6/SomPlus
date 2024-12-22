# SomPlus
Looks at changes in the grades and schedule via the [Somtoday API](https://github.com/elisaado/somtoday-api-docs).

Relies on the files refreshtoken.txt, gradelist.pkl, schedule.pkl, week_number.txt and standard_schedule.pkl. You can replace the .pkl for .json if you want.

The Somtoday API auth is a mess. I use [Somtoday SSO tool](https://github.com/m-caeliusrufus/Somtoday-SSO-tool) to get the refreshtoken, and put that in the refreshtoken.txt. You can also use [SomtodaySSOLogin](https://github.com/Underlyingglitch/SomtodaySSOLogin) for this.

The schedule section only uses items with a defined starting hour, so any items that don't align with standard lesson times are not used. You could just save the times from the data directly, but that would cause the notification generator to break.

Things you need to adjust for the script to work: (these things work very differently for all schools)
* `lln_id` in **grades_main** (not your "leerlingnummer" but the id you get via /rest/v1/account/)
* The process of removing columntypes in **grades_main**

   You can see all the types in the raw data from .../rest/v1/resultaten/huidigVoorLeerling/...
  
   Usually only `toetskolom` is needed if you're working with grades from tests. If you're working with grades from the periods/reports, you need either `PeriodeGemiddeldeKolom` or `RapportGemiddeldeKolom`. On most schools one of them is rounded and the other is not (I think), but it differs, so just look wich one does the thing you want :D


* `subjects_to_remove` in **grades_main** 
* `maximum_amount_lessons` in **schedule_notification_generator** AND **schedule_main** AND **saveStandardSchedule.py**
* `subjects_in_schedule` in **schedule_main**
* `btoken` in **saveStandardSchedule.py** (you only need to save a new standard schedule if you have a new one, so you can just generate a extra token when you need to run this script)
