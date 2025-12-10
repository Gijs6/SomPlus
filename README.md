# SomPlus

Automated monitoring for Somtoday. Tracks grade and schedule changes, sends you notifications when something changes.

## Setup

Here's how to run SomPlus yourself with Docker.

### Step 1: Get your Somtoday credentials

You need two things from Somtoday: a **refresh token** and your **leerling id**.

Easiest way to get these is with my [Firefox extension](https://addons.mozilla.org/en-GB/firefox/addon/somtoday-token-taker/).

### Step 2: Get notification credentials

#### Pushsafer

1. Sign up at pushsafer.com
2. Get your API key from account settings
3. Get a device or group ID from your dashboard

#### Discord webhook

1. Go to your Discord server settings
2. Go to Integrations > Webhooks
3. Create a new webhook and copy the URL

### Step 3: Create directories

Create the directory structure on your server:

```bash
mkdir -p /.../somplus/config/users
mkdir -p /.../somplus/data
mkdir -p /.../somplus/logs
```

### Step 4: Create app config

Create `/.../somplus/config/app.json` with this:

```json
{
    "somtoday": {
        "api_base": "https://api.somtoday.nl/rest/v1",
        "oauth_url": "https://inloggen.somtoday.nl/oauth2/token",
        "client_id": "somtoday-leerling-web",
        "pagination_size": 100
    },
    "logging": {
        "daily_log_retention": 250,
        "error_log_retention": 30,
        "error_summary_interval": 3600,
        "timezone": "Europe/Amsterdam"
    },
    "scheduler": {
        "sleep_schedule": [
            { "start": [23, 0], "end": [6, 0], "sleep": 300 },
            { "start": [6, 0], "end": [6, 30], "sleep": 90 },
            { "start": [6, 30], "end": [7, 30], "sleep": 45 },
            { "start": [7, 30], "end": [9, 0], "sleep": 80 },
            { "start": [9, 0], "end": [13, 0], "sleep": 75 },
            { "start": [13, 0], "end": [15, 0], "sleep": 60 },
            { "start": [15, 0], "end": [18, 0], "sleep": 80 },
            { "start": [18, 0], "end": [23, 0], "sleep": 120 }
        ]
    }
}
```

As far as I know, the API and OAuth URLs are the same across all schools, but they might differ.

Feel free to adjust the sleep schedule times to your liking.

### Step 5: Create user configs

Create a config file for each person you want to monitor.

Make `/.../somplus/config/users/NAME.json` with this (replace NAME with whatever you want):

```json
{
    "enabled": true,
    "display_name": "John",
    "auth": {
        "refresh_token": "PUT_YOUR_REFRESH_TOKEN_HERE",
        "leerling_id": "PUT_YOUR_LEERLING_ID_HERE"
    },
    "monitoring": {
        "grades": {
            "enabled": true,
            "filters": {
                "exclude_subjects": ["MEN", "LO"],
                "exclude_types": [
                    "PeriodeGemiddeldeKolom",
                    "RapportGemiddeldeKolom"
                ]
            }
        },
        "schedule": {
            "enabled": true
        }
    },
    "notifications": {
        "pushsafer": {
            "grades": {
                "enabled": true,
                "api_key": "YOUR_PUSHSAFER_KEY",
                "device_id": "device123",
                "sound_high": 21,
                "sound_medium": 18,
                "sound_low": 42,
                "breakpoint_high": 7.5,
                "breakpoint_medium": 5.5,
                "icon": 2,
                "priority": 2
            },
            "schedule": {
                "enabled": true,
                "api_key": "YOUR_PUSHSAFER_KEY",
                "device_id": "device123",
                "sound": 18,
                "icon": 2,
                "priority": 2
            }
        }
    },
    "discord": {
        "grades": {
            "enabled": true,
            "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
            "mention_role_id": "ROLE_ID_OPTIONAL",
            "tts": true,
            "color_high": 5763719,
            "color_medium": 3447003,
            "color_low": 15158332,
            "breakpoint_high": 7.5,
            "breakpoint_medium": 5.5
        },
        "schedule": {
            "enabled": true,
            "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
            "mention_role_id": "ROLE_ID_OPTIONAL",
            "tts": true,
            "color_changes": 16730652,
            "color_current": 2326507
        }
    },
    "state": {}
}
```

You can remove Discord and/or Pushsafer sections if you only want to use one.

### Step 6: Start the container

Start the Docker container:

```bash
docker run -d \
  --name somplus \
  --restart unless-stopped \
  -v /.../somplus/config:/app/config:ro \
  -v /.../somplus/data:/app/data \
  -v /.../somplus/logs:/app/logs \
  -e TZ=Europe/Amsterdam \
  ghcr.io/gijs6/somplus:latest
```

### Step 7: Check if it's working

Watch the logs:

```bash
docker logs -f somplus
```

## How it works

The container runs continuously, checking Somtoday at different intervals based on your sleep schedule. Here's what happens on each check:

1. **Token refresh** - Automatically refreshes your Somtoday auth token
2. **Grade monitoring** - Grabs all your grades, compares them with cached data, looks for changes (NEW, CHANGED, REMOVED)
3. **Schedule monitoring** - Gets current/next week's schedule based on rollover settings, compares with cache, finds changes (UITVAL, SUBJECT_CHANGE, etc.)
4. **Notifications** - Sends you a notification immediately for each change
5. **Error handling** - Logs errors and sends hourly summaries if you configured error notifications

**How week switching works:**

- If today > `weekend_rollover_day` (default: Friday): checks next week
- If today = `weekend_rollover_day` AND time >= `weekend_rollover_hour` (default: 16): checks next week
- Otherwise: checks current week

When a new week starts, the app searches ahead (default: 8 weeks) to find the week with the most lessons and uses that as your "standard schedule" baseline.

## Troubleshooting

- Make sure `enabled: true` in your user config
- Make sure the notification type you want is enabled (grades/schedule)
- Double check your API keys and webhook URLs are correct
- If your refresh token expired, grab a new one from Somtoday

## Config reference

### User config (`config/users/name.json`)

#### Basic structure

```json
{
  "enabled": true,
  "display_name": "Name",
  "auth": { ... },
  "monitoring": { ... },
  "notifications": { ... },
  "state": {}
}
```

#### Root level fields

| Field                | Type    | Required | Description                                                       |
| -------------------- | ------- | -------- | ----------------------------------------------------------------- |
| `enabled`            | boolean | Yes      | Set to `false` to temporarily turn off monitoring for this person |
| `display_name`       | string  | Yes      | Name that shows up in notifications                               |
| `auth.refresh_token` | string  | Yes      | Your Somtoday refresh token from step 1                           |
| `auth.leerling_id`   | string  | Yes      | Your Somtoday leerling ID from step 1                             |
| `state`              | object  | Yes      | Leave this empty, the app manages it automatically                |

#### `monitoring.grades`

| Field                      | Type     | Default | Description                                          |
| -------------------------- | -------- | ------- | ---------------------------------------------------- |
| `enabled`                  | boolean  | -       | Turn on grade monitoring                             |
| `filters.exclude_subjects` | string[] | `[]`    | Subject codes to ignore, like `["MEN", "LO", "CKV"]` |
| `filters.exclude_types`    | string[] | `[]`    | Grade types to skip - usually period/report averages |

#### `monitoring.schedule`

| Field                           | Type    | Default | Description                                                                  |
| ------------------------------- | ------- | ------- | ---------------------------------------------------------------------------- |
| `enabled`                       | boolean | -       | Turn on schedule monitoring                                                  |
| `weekend_rollover_hour`         | number  | `16`    | Hour (0-23) when to switch to checking next week's schedule                  |
| `weekend_rollover_day`          | number  | `4`     | Day when the week switches (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun) |
| `schedule_fetch_end_day`        | number  | `5`     | Last day of the week to grab (0=Mon through 6=Sun)                           |
| `standard_schedule_weeks_ahead` | number  | `8`     | How many weeks ahead to search for finding your baseline schedule            |

#### `notifications.pushsafer.grades`

| Field               | Type    | Default | Description                                           |
| ------------------- | ------- | ------- | ----------------------------------------------------- |
| `enabled`           | boolean | -       | Turn on Pushsafer notifications for grades            |
| `api_key`           | string  | -       | Your Pushsafer API key                                |
| `device_id`         | string  | -       | Your Pushsafer device ID                              |
| `sound_high`        | number  | `21`    | Sound to play for high grades (≥ breakpoint_high)     |
| `sound_medium`      | number  | `18`    | Sound to play for medium grades (≥ breakpoint_medium) |
| `sound_low`         | number  | `42`    | Sound to play for low grades (< breakpoint_medium)    |
| `breakpoint_high`   | number  | `7.5`   | Grade threshold for high sound                        |
| `breakpoint_medium` | number  | `5.5`   | Grade threshold for medium sound                      |
| `icon`              | number  | `2`     | Pushsafer icon ID                                     |
| `priority`          | number  | `2`     | Notification priority (-2 to 2)                       |

#### `notifications.pushsafer.schedule`

Same fields as grades notifications but for schedule changes.

#### `notifications.pushsafer.errors`

| Field       | Type    | Default | Description                                |
| ----------- | ------- | ------- | ------------------------------------------ |
| `enabled`   | boolean | -       | Turn on Pushsafer notifications for errors |
| `api_key`   | string  | -       | Your Pushsafer API key                     |
| `device_id` | string  | -       | Your Pushsafer device ID                   |
| `sound`     | number  | `42`    | Sound to play for errors                   |
| `icon`      | number  | `2`     | Pushsafer icon ID                          |
| `priority`  | number  | `2`     | Notification priority (-2 to 2)            |

**Note:** Errors get batched and sent hourly (not immediately). Interval is set in `app.json`.

#### `notifications.discord.grades`

| Field               | Type    | Default    | Description                              |
| ------------------- | ------- | ---------- | ---------------------------------------- |
| `enabled`           | boolean | -          | Turn on Discord notifications for grades |
| `webhook_url`       | string  | -          | Your Discord webhook URL                 |
| `mention_role_id`   | string  | -          | Role ID to ping (optional)               |
| `tts`               | boolean | `true`     | Text-to-speech on or off                 |
| `color_high`        | number  | `5763719`  | Embed color for high grades (green)      |
| `color_medium`      | number  | `3447003`  | Embed color for medium grades (blue)     |
| `color_low`         | number  | `15158332` | Embed color for low grades (red)         |
| `breakpoint_high`   | number  | `7.5`      | Grade threshold for high color           |
| `breakpoint_medium` | number  | `5.5`      | Grade threshold for medium color         |

#### `notifications.discord.schedule`

| Field             | Type    | Default    | Description                                        |
| ----------------- | ------- | ---------- | -------------------------------------------------- |
| `enabled`         | boolean | -          | Turn on Discord notifications for schedule changes |
| `webhook_url`     | string  | -          | Your Discord webhook URL                           |
| `mention_role_id` | string  | -          | Role ID to ping (optional)                         |
| `tts`             | boolean | `true`     | Text-to-speech on or off                           |
| `color_changes`   | number  | `16730652` | Embed color for changes (orange)                   |
| `color_current`   | number  | `2326507`  | Embed color for current schedule (blue)            |

#### `notifications.discord.errors`

| Field         | Type    | Default    | Description                              |
| ------------- | ------- | ---------- | ---------------------------------------- |
| `enabled`     | boolean | -          | Turn on Discord notifications for errors |
| `webhook_url` | string  | -          | Your Discord webhook URL                 |
| `tts`         | boolean | `false`    | Text-to-speech on or off                 |
| `color`       | number  | `16711680` | Embed color (red)                        |

**Note:** Errors get batched and sent hourly (not immediately). Interval is set in `app.json`.

### App config (`config/app.json`)

#### `somtoday`

| Field             | Type   | Default | Description                                         |
| ----------------- | ------ | ------- | --------------------------------------------------- |
| `api_base`        | string | -       | Somtoday REST API endpoint (usually doesn't change) |
| `oauth_url`       | string | -       | OAuth token endpoint (usually doesn't change)       |
| `client_id`       | string | -       | OAuth client ID (usually doesn't change)            |
| `pagination_size` | number | `100`   | How many grades to grab per API request             |

#### `logging`

| Field                    | Type   | Default              | Description                                |
| ------------------------ | ------ | -------------------- | ------------------------------------------ |
| `daily_log_retention`    | number | `250`                | How many days to keep daily logs           |
| `error_log_retention`    | number | `30`                 | How many days to keep error logs           |
| `error_summary_interval` | number | `3600`               | Seconds between error notification batches |
| `timezone`               | string | `"Europe/Amsterdam"` | Timezone for log timestamps                |

#### `scheduler.sleep_schedule`

Array of time windows that control how often to check Somtoday. Each entry has:

| Field   | Type     | Description                                               |
| ------- | -------- | --------------------------------------------------------- |
| `start` | number[] | Start time as `[hour, minute]`, like `[6, 30]` for 6:30am |
| `end`   | number[] | End time as `[hour, minute]`, like `[9, 0]` for 9:00am    |
| `sleep` | number   | Seconds to wait between checks during this window         |

## Local development

Want to run this locally without Docker:

```bash
git clone https://github.com/Gijs6/SomPlus.git
cd somplus
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run once:

```bash
python run.py
```

Run continuously:

```bash
python scheduler.py
```
