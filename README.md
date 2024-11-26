# SomPlus
Looks at changes in the grades and schedule via the [Somtoday API](https://github.com/elisaado/somtoday-api-docs).

Relies on the files refreshtoken.txt, gradelist.pkl, schedule.pkl, week_number.txt and standard_schedule.pkl. You can replace the .pkl for .json if you want.

The Somtoday API auth is a mess. I use [Somtoday SSO tool](https://github.com/m-caeliusrufus/Somtoday-SSO-tool) to get the refreshtoken, and put that in the refreshtoken.txt

Things you need to adjust for the script to work: (these things work very differently for all schools)
* `lln_id` in **grades_main** (not your "leerlingnummer" but the id you get via /rest/v1/account/)
* `types_to_remove` in **grades_main** (you can see all the types in the raw data from .../rest/v1/resultaten/huidigVoorLeerling/..., usually only "toetskolom" is needed if you're working with grades from tests)
* `subjects_to_remove` in **grades_main** 
* `maximum_amount_lessons` in **schedule_notification_generator**, **schedule_main** AND **saveStandardSchedule.py**
* `subjects_in_schedule` in **schedule_main**
* `btoken` in **saveStandardSchedule.py** (you only need to save a new standard schedule if you have a new one, so you can just generate a extra token when you need to run this script)
