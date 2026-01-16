# Config reference

## Example configs

### `config/app.json`

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
            { "start": [6, 0], "end": [7, 30], "sleep": 60 },
            { "start": [7, 30], "end": [15, 0], "sleep": 75 },
            { "start": [15, 0], "end": [23, 0], "sleep": 100 }
        ]
    }
}
```

### `config/users/yourname.json`

```json
{
    "enabled": true,
    "display_name": "Your Name",
    "auth": {
        "refresh_token": "YOUR_REFRESH_TOKEN",
        "leerling_id": "YOUR_LEERLING_ID"
    },
    "monitoring": {
        "grades": { "enabled": true },
        "schedule": { "enabled": true }
    },
    "notifications": {
        "pushsafer": {
            "grades": { "enabled": true, "api_key": "KEY", "device_id": "ID" },
            "schedule": { "enabled": true, "api_key": "KEY", "device_id": "ID" }
        }
    },
    "discord": {
        "grades": { "enabled": true, "webhook_url": "YOUR_WEBHOOK" },
        "schedule": { "enabled": true, "webhook_url": "YOUR_WEBHOOK" }
    }
}
```

---

## All options

### User config (`config/users/name.json`)

### Root level fields

| Field                | Type    | Required | Description                                                       |
| -------------------- | ------- | -------- | ----------------------------------------------------------------- |
| `enabled`            | boolean | Yes      | Set to `false` to temporarily turn off monitoring for this person |
| `display_name`       | string  | Yes      | Name that shows up in notifications                               |
| `auth.refresh_token` | string  | Yes      | Your Somtoday refresh token from step 1                           |
| `auth.leerling_id`   | string  | Yes      | Your Somtoday leerling ID from step 1                             |

### `monitoring.grades`

| Field                      | Type     | Default | Description                                          |
| -------------------------- | -------- | ------- | ---------------------------------------------------- |
| `enabled`                  | boolean  | -       | Turn on grade monitoring                             |
| `filters.exclude_subjects` | string[] | `[]`    | Subject codes to ignore, like `["MEN", "LO", "CKV"]` |
| `filters.exclude_types`    | string[] | `[]`    | Grade types to skip - usually period/report averages |

### `monitoring.schedule`

| Field                           | Type    | Default | Description                                                                  |
| ------------------------------- | ------- | ------- | ---------------------------------------------------------------------------- |
| `enabled`                       | boolean | -       | Turn on schedule monitoring                                                  |
| `weekend_rollover_hour`         | number  | `16`    | Hour (0-23) when to switch to checking next week's schedule                  |
| `weekend_rollover_day`          | number  | `4`     | Day when the week switches (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun) |
| `schedule_fetch_end_day`        | number  | `5`     | Last day of the week to grab (0=Mon through 6=Sun)                           |
| `standard_schedule_weeks_ahead` | number  | `8`     | How many weeks ahead to search for finding your baseline schedule            |

### `notifications.pushsafer.grades`

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

### `notifications.pushsafer.schedule`

Same fields as grades notifications but for schedule changes.

### `notifications.pushsafer.errors`

| Field       | Type    | Default | Description                                |
| ----------- | ------- | ------- | ------------------------------------------ |
| `enabled`   | boolean | -       | Turn on Pushsafer notifications for errors |
| `api_key`   | string  | -       | Your Pushsafer API key                     |
| `device_id` | string  | -       | Your Pushsafer device ID                   |
| `sound`     | number  | `42`    | Sound to play for errors                   |
| `icon`      | number  | `2`     | Pushsafer icon ID                          |
| `priority`  | number  | `2`     | Notification priority (-2 to 2)            |

**Note:** Errors get batched and sent hourly (not immediately). Interval is set in `app.json`.

### `notifications.discord.grades`

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

### `notifications.discord.schedule`

| Field             | Type    | Default    | Description                                        |
| ----------------- | ------- | ---------- | -------------------------------------------------- |
| `enabled`         | boolean | -          | Turn on Discord notifications for schedule changes |
| `webhook_url`     | string  | -          | Your Discord webhook URL                           |
| `mention_role_id` | string  | -          | Role ID to ping (optional)                         |
| `tts`             | boolean | `true`     | Text-to-speech on or off                           |
| `color_changes`   | number  | `16730652` | Embed color for changes (orange)                   |
| `color_current`   | number  | `2326507`  | Embed color for current schedule (blue)            |

### `notifications.discord.errors`

| Field         | Type    | Default    | Description                              |
| ------------- | ------- | ---------- | ---------------------------------------- |
| `enabled`     | boolean | -          | Turn on Discord notifications for errors |
| `webhook_url` | string  | -          | Your Discord webhook URL                 |
| `tts`         | boolean | `false`    | Text-to-speech on or off                 |
| `color`       | number  | `16711680` | Embed color (red)                        |

**Note:** Errors get batched and sent hourly (not immediately). Interval is set in `app.json`.

## App config (`config/app.json`)

### `somtoday`

| Field             | Type   | Default | Description                                         |
| ----------------- | ------ | ------- | --------------------------------------------------- |
| `api_base`        | string | -       | Somtoday REST API endpoint (usually doesn't change) |
| `oauth_url`       | string | -       | OAuth token endpoint (usually doesn't change)       |
| `client_id`       | string | -       | OAuth client ID (usually doesn't change)            |
| `pagination_size` | number | `100`   | How many grades to grab per API request             |

### `logging`

| Field                    | Type   | Default              | Description                                |
| ------------------------ | ------ | -------------------- | ------------------------------------------ |
| `daily_log_retention`    | number | `250`                | How many days to keep daily logs           |
| `error_log_retention`    | number | `30`                 | How many days to keep error logs           |
| `error_summary_interval` | number | `3600`               | Seconds between error notification batches |
| `timezone`               | string | `"Europe/Amsterdam"` | Timezone for log timestamps                |

### `scheduler.sleep_schedule`

Array of time windows that control how often to check Somtoday. Each entry has:

| Field   | Type     | Description                                               |
| ------- | -------- | --------------------------------------------------------- |
| `start` | number[] | Start time as `[hour, minute]`, like `[6, 30]` for 6:30am |
| `end`   | number[] | End time as `[hour, minute]`, like `[9, 0]` for 9:00am    |
| `sleep` | number   | Seconds to wait between checks during this window         |
