import os
import json
from datetime import datetime, timedelta

log_dir = None
error_tracking = {}


def init_logging(logs_dir):
    global log_dir
    log_dir = logs_dir
    os.makedirs(os.path.join(logs_dir, "daily"), exist_ok=True)
    os.makedirs(os.path.join(logs_dir, "errors"), exist_ok=True)
    load_error_tracking()


def get_daily_log_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(log_dir, "daily", f"{today}.log")


def get_error_tracking_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(log_dir, "errors", f"{today}_errors.json")


def load_error_tracking():
    global error_tracking
    path = get_error_tracking_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            error_tracking = json.load(f)
    else:
        error_tracking = {}


def save_error_tracking():
    path = get_error_tracking_path()
    with open(path, "w") as f:
        json.dump(error_tracking, f, indent=2)


def get_current_hour_key():
    now = datetime.now()
    return now.strftime("%Y-%m-%dT%H:00:00")


RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def console_print(message, indent=0, color="", bold=False):
    indent_str = " " * indent
    style = ""
    if bold:
        style += BOLD
    if color:
        style += color
    if style:
        print(f"{style}{indent_str}{message}{RESET}")
    else:
        print(f"{indent_str}{message}")


def console_info(message, indent=0):
    console_print(f"[INFO] {message}", indent=indent)


def console_success(message, indent=0):
    console_print(f"[OK] {message}", indent=indent, color=GREEN, bold=True)


def console_error(message, indent=0):
    console_print(f"[ERROR] {message}", indent=indent, color=RED, bold=True)


def console_warning(message, indent=0):
    console_print(f"[WARNING] {message}", indent=indent, color=YELLOW, bold=True)


def log_info(username, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {username} | INFO | {message}\n"
    with open(get_daily_log_path(), "a") as f:
        f.write(log_line)
    console_print(f"[{username}] {message}", indent=2)


def log_error(username, message, exception=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    error_detail = message
    if exception:
        error_detail = f"{message}: {str(exception)}"

    console_print(f"[{username}] ERROR: {error_detail}", indent=2, color=RED, bold=True)

    if log_dir is None:
        return

    log_line = f"{timestamp} | {username} | ERROR | {error_detail}\n"
    with open(get_daily_log_path(), "a") as f:
        f.write(log_line)

    hour_key = get_current_hour_key()
    if hour_key not in error_tracking:
        error_tracking[hour_key] = {}
    if username not in error_tracking[hour_key]:
        error_tracking[hour_key][username] = []

    error_tracking[hour_key][username].append(
        {"time": datetime.now().strftime("%H:%M:%S"), "error": error_detail}
    )
    save_error_tracking()


def get_hour_errors(hour_key=None):
    if hour_key is None:
        hour_key = get_current_hour_key()
    return error_tracking.get(hour_key, {})


def get_previous_hour_errors():
    now = datetime.now()
    previous_hour = now - timedelta(hours=1)
    hour_key = previous_hour.strftime("%Y-%m-%dT%H:00:00")
    return get_hour_errors(hour_key), hour_key


def clear_hour_errors(hour_key):
    if hour_key in error_tracking:
        del error_tracking[hour_key]
        save_error_tracking()


def rotate_logs(retention_days, error_retention_days=30):
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    daily_dir = os.path.join(log_dir, "daily")
    if os.path.exists(daily_dir):
        for filename in os.listdir(daily_dir):
            if filename.endswith(".log"):
                date_str = filename.replace(".log", "")
                try:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        os.remove(os.path.join(daily_dir, filename))
                except ValueError:
                    pass

    error_dir = os.path.join(log_dir, "errors")
    error_cutoff = datetime.now() - timedelta(days=error_retention_days)
    if os.path.exists(error_dir):
        for filename in os.listdir(error_dir):
            if filename.endswith("_errors.json"):
                date_str = filename.replace("_errors.json", "")
                try:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date < error_cutoff:
                        os.remove(os.path.join(error_dir, filename))
                except ValueError:
                    pass
