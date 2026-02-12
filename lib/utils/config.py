_MISSING = object()


def get(config, path, default=None):
    keys = path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key, _MISSING)
            if value is _MISSING:
                return default
        else:
            return default

    if value is None and default is not None:
        return default

    return value


def get_schedule_enabled(user_config):
    return get(user_config, "monitoring.schedule.enabled", True)


def get_schedule_filters(user_config):
    return get(user_config, "monitoring.schedule.filters", {})


def get_weekend_rollover_hour(user_config):
    return get(user_config, "monitoring.schedule.weekend_rollover_hour", 16)


def get_weekend_rollover_day(user_config):
    return get(user_config, "monitoring.schedule.weekend_rollover_day", 4)


def get_schedule_fetch_end_day(user_config):
    return get(user_config, "monitoring.schedule.schedule_fetch_end_day", 5)


def get_standard_schedule_weeks_ahead(user_config):
    return get(user_config, "monitoring.schedule.standard_schedule_weeks_ahead", 8)


def get_grades_enabled(user_config):
    return get(user_config, "monitoring.grades.enabled", True)


def get_grades_filters(user_config):
    return get(
        user_config,
        "monitoring.grades.filters",
        {"exclude_subjects": [], "exclude_types": []},
    )


def get_discord_grades_enabled(user_config):
    return get(user_config, "notifications.discord.grades.enabled", False)


def get_discord_grades_webhook_url(user_config):
    return get(user_config, "notifications.discord.grades.webhook_url")


def get_discord_grades_mention_role_id(user_config):
    return get(user_config, "notifications.discord.grades.mention_role_id")


def get_discord_grades_tts(user_config):
    return get(user_config, "notifications.discord.grades.tts", True)


def get_discord_grades_color(user_config):
    return get(user_config, "notifications.discord.grades.color", 16730652)


def get_discord_grades_color_high(user_config):
    return get(user_config, "notifications.discord.grades.color_high", 5763719)


def get_discord_grades_color_medium(user_config):
    return get(user_config, "notifications.discord.grades.color_medium", 3447003)


def get_discord_grades_color_low(user_config):
    return get(user_config, "notifications.discord.grades.color_low", 15158332)


def get_discord_grades_breakpoint_high(user_config):
    return get(user_config, "notifications.discord.grades.breakpoint_high", 7.5)


def get_discord_grades_breakpoint_medium(user_config):
    return get(user_config, "notifications.discord.grades.breakpoint_medium", 5.5)


def get_discord_schedule_enabled(user_config):
    return get(user_config, "notifications.discord.schedule.enabled", False)


def get_discord_schedule_webhook_url(user_config):
    return get(user_config, "notifications.discord.schedule.webhook_url")


def get_discord_schedule_mention_role_id(user_config):
    return get(user_config, "notifications.discord.schedule.mention_role_id")


def get_discord_schedule_tts(user_config):
    return get(user_config, "notifications.discord.schedule.tts", True)


def get_discord_schedule_color_changes(user_config):
    return get(user_config, "notifications.discord.schedule.color_changes", 16730652)


def get_discord_schedule_color_current(user_config):
    return get(user_config, "notifications.discord.schedule.color_current", 2326507)


def get_discord_errors_enabled(user_config):
    return get(user_config, "notifications.discord.errors.enabled", False)


def get_discord_errors_webhook_url(user_config):
    return get(user_config, "notifications.discord.errors.webhook_url")


def get_discord_errors_mention_role_id(user_config):
    return get(user_config, "notifications.discord.errors.mention_role_id")


def get_discord_errors_tts(user_config):
    return get(user_config, "notifications.discord.errors.tts", False)


def get_discord_errors_color(user_config):
    return get(user_config, "notifications.discord.errors.color", 16711680)


def get_pushsafer_grades_enabled(user_config):
    return get(user_config, "notifications.pushsafer.grades.enabled", False)


def get_pushsafer_grades_api_key(user_config):
    return get(user_config, "notifications.pushsafer.grades.api_key")


def get_pushsafer_grades_device_id(user_config):
    return get(user_config, "notifications.pushsafer.grades.device_id")


def get_pushsafer_grades_sound_high(user_config):
    return get(user_config, "notifications.pushsafer.grades.sound_high", 21)


def get_pushsafer_grades_sound_medium(user_config):
    return get(user_config, "notifications.pushsafer.grades.sound_medium", 18)


def get_pushsafer_grades_sound_low(user_config):
    return get(user_config, "notifications.pushsafer.grades.sound_low", 42)


def get_pushsafer_grades_breakpoint_high(user_config):
    return get(user_config, "notifications.pushsafer.grades.breakpoint_high", 7.5)


def get_pushsafer_grades_breakpoint_medium(user_config):
    return get(user_config, "notifications.pushsafer.grades.breakpoint_medium", 5.5)


def get_pushsafer_grades_icon(user_config):
    return get(user_config, "notifications.pushsafer.grades.icon", 2)


def get_pushsafer_grades_priority(user_config):
    return get(user_config, "notifications.pushsafer.grades.priority", 2)


def get_pushsafer_schedule_enabled(user_config):
    return get(user_config, "notifications.pushsafer.schedule.enabled", False)


def get_pushsafer_schedule_api_key(user_config):
    return get(user_config, "notifications.pushsafer.schedule.api_key")


def get_pushsafer_schedule_device_id(user_config):
    return get(user_config, "notifications.pushsafer.schedule.device_id")


def get_pushsafer_schedule_sound(user_config):
    return get(user_config, "notifications.pushsafer.schedule.sound", 18)


def get_pushsafer_schedule_icon(user_config):
    return get(user_config, "notifications.pushsafer.schedule.icon", 2)


def get_pushsafer_schedule_priority(user_config):
    return get(user_config, "notifications.pushsafer.schedule.priority", 2)


def get_pushsafer_errors_enabled(user_config):
    return get(user_config, "notifications.pushsafer.errors.enabled", False)


def get_pushsafer_errors_api_key(user_config):
    return get(user_config, "notifications.pushsafer.errors.api_key")


def get_pushsafer_errors_device_id(user_config):
    return get(user_config, "notifications.pushsafer.errors.device_id")


def get_pushsafer_errors_sound(user_config):
    return get(user_config, "notifications.pushsafer.errors.sound", 42)


def get_pushsafer_errors_icon(user_config):
    return get(user_config, "notifications.pushsafer.errors.icon", 2)


def get_pushsafer_errors_priority(user_config):
    return get(user_config, "notifications.pushsafer.errors.priority", 2)


def get_webhook_url(user_config, notifier_type):
    if notifier_type == "discord":
        return (
            get_discord_grades_webhook_url(user_config)
            or get_discord_schedule_webhook_url(user_config)
            or get_discord_errors_webhook_url(user_config)
        )
    elif notifier_type == "pushsafer":
        return (
            get_pushsafer_grades_api_key(user_config)
            or get_pushsafer_schedule_api_key(user_config)
            or get_pushsafer_errors_api_key(user_config)
        )
    return None
