import os
import json
from datetime import datetime
from lib.utils import logger, config
from lib.services.somtoday_api import SomTodayAPI
from lib.monitors.grade_monitor import GradeMonitor
from lib.monitors.schedule_monitor import ScheduleMonitor
from lib.notifiers.pushsafer import PushSaferNotifier
from lib.notifiers.discord import DiscordNotifier


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_user_config(username, config, config_dir):
    users_dir = os.path.join(config_dir, "users")
    os.makedirs(users_dir, exist_ok=True)
    path = os.path.join(users_dir, f"{username}.json")
    save_json(path, config)


def load_all_user_configs(config_dir):
    users_dir = os.path.join(config_dir, "users")
    if not os.path.exists(users_dir):
        return {}

    user_configs = {}
    for filename in os.listdir(users_dir):
        if filename.endswith(".json"):
            username = filename[:-5]
            path = os.path.join(users_dir, filename)
            user_configs[username] = load_json(path)

    return user_configs


def process_user(username, user_config, app_config, api, monitors, notifiers):
    if not config.get(user_config, "enabled", True):
        logger.log_info(username, "User disabled, skipping")
        return

    logger.console_print(f"\n{'=' * 60}")
    logger.console_info(f"Processing user: {username}")
    logger.console_print(f"{'=' * 60}")

    try:
        refresh_token = config.get(user_config, "auth.refresh_token")
        logger.console_print("Refreshing authentication token...", indent=2)
        access_token, new_refresh_token = api.refresh_token(refresh_token)

        if new_refresh_token != refresh_token:
            user_config["auth"]["refresh_token"] = new_refresh_token
            save_user_config(username, user_config, app_config["paths"]["config_dir"])
            logger.console_print("Token updated and saved", indent=2)

        logger.log_info(username, "Token refreshed successfully")

    except Exception as e:
        logger.log_error(username, "Token refresh failed", e)
        return

    for monitor in monitors:
        try:
            logger.console_print(f"\nRunning {monitor.__class__.__name__}...", indent=2)
            monitor.run(access_token, notifiers)
        except Exception as e:
            logger.log_error(username, f"{monitor.__class__.__name__} failed", e)

    if not user_config.get("state"):
        user_config["state"] = {}

    user_config["state"]["last_successful_run"] = datetime.now().isoformat()
    save_user_config(username, user_config, app_config["paths"]["config_dir"])
    logger.console_success("User processing completed", indent=2)


def check_hourly_errors(user_configs, notifiers):
    errors, hour_key = logger.get_previous_hour_errors()

    if not errors:
        logger.console_info("No errors from previous hour to report")
        return

    logger.console_print(f"\n{'=' * 60}")
    logger.console_info(f"Processing hourly error notifications ({hour_key})")
    logger.console_print(f"{'=' * 60}")
    total_errors = sum(len(error_list) for error_list in errors.values())
    logger.console_print(
        f"Found {total_errors} error(s) for {len(errors)} user(s)", indent=2
    )

    for username, error_list in errors.items():
        if username not in user_configs:
            continue

        logger.console_print(f"Sending error notifications for {username}...", indent=2)
        for notifier in notifiers:
            try:
                notifier.send_error_notification(
                    username, user_configs[username], {username: error_list}
                )
            except Exception as e:
                logger.log_error(username, "Failed to send error notification", e)

    logger.clear_hour_errors(hour_key)
    logger.console_success("Error notifications sent and cleared", indent=2)


def main():
    logger.console_print("\n" + "*" * 20)
    logger.console_print("*" + " " * 18 + "*")
    logger.console_print(f"*{'SomPlus':^18}*")
    logger.console_print("*" + " " * 18 + "*")
    logger.console_print("*" * 20 + "\n")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config", "app.json")

    logger.console_info(f"Loading configuration from: {config_path}")
    try:
        app_config = load_json(config_path)
        app_config["paths"] = {
            "config_dir": os.path.join(base_dir, "config"),
            "data_dir": os.path.join(base_dir, "data"),
            "logs_dir": os.path.join(base_dir, "logs"),
        }
    except Exception as e:
        logger.log_error("system", "Failed to load configuration", e)
        return

    try:
        logger.init_logging(app_config["paths"]["logs_dir"])
        logger.console_success(
            f"Initialized logging: {app_config['paths']['logs_dir']}"
        )
    except Exception as e:
        logger.log_error("system", "Failed to initialize logging", e)
        return

    try:
        api = SomTodayAPI(
            app_config["somtoday"]["api_base"],
            app_config["somtoday"]["oauth_url"],
            app_config["somtoday"]["client_id"],
            app_config["somtoday"].get("pagination_size", 100),
        )
        logger.console_success("Initialized API client")
    except Exception as e:
        logger.log_error("system", "Failed to initialize API client", e)
        return

    try:
        user_configs = load_all_user_configs(app_config["paths"]["config_dir"])
        logger.console_success(
            f"Loaded {len(user_configs)} user configuration(s): {', '.join(user_configs.keys())}"
        )
    except Exception as e:
        logger.log_error("system", "Failed to load user configurations", e)
        return

    try:
        notifiers = [PushSaferNotifier(), DiscordNotifier()]
        logger.console_success(f"Initialized {len(notifiers)} notifier(s)\n")
    except Exception as e:
        logger.log_error("system", "Failed to initialize notifiers", e)
        return

    check_hourly_errors(user_configs, notifiers)

    for username, user_config in user_configs.items():
        monitors = [
            GradeMonitor(username, user_config, app_config, api),
            ScheduleMonitor(username, user_config, app_config, api),
        ]
        process_user(username, user_config, app_config, api, monitors, notifiers)

    logger.console_print(f"\n{'=' * 60}")
    try:
        daily_retention = app_config["logging"]["daily_log_retention"]
        error_retention = app_config["logging"].get("error_log_retention", 30)
        logger.console_info(
            f"Rotating logs (daily: {daily_retention} days, errors: {error_retention} days)..."
        )
        logger.rotate_logs(daily_retention, error_retention)
        logger.console_success("Completed log rotation")
    except Exception as e:
        logger.log_error("system", "Failed to rotate logs", e)

    logger.console_print("\n" + "*" * 60)
    logger.console_success("All tasks completed successfully!")
    logger.console_print("*" * 60 + "\n")


if __name__ == "__main__":
    main()
