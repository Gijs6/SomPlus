import os
import json
from lib.utils import logger


class BaseMonitor:
    def __init__(self, username, user_config, app_config, api):
        self.username = username
        self.user_config = user_config
        self.app_config = app_config
        self.api = api
        self.data_dir = app_config["paths"]["data_dir"]

    def run(self, access_token, notifiers):
        if not self.is_enabled():
            logger.console_info(f"{self.__class__.__name__} disabled, skipping", indent=4)
            return

        logger.console_print("Fetching data from API...", indent=4)
        try:
            raw_data = self.fetch_data(access_token)
        except Exception as e:
            logger.console_error(f"Failed to fetch data: {e}", indent=4)
            return

        logger.console_print("Processing data...", indent=4)
        try:
            processed_data = self.process_data(raw_data)
        except Exception as e:
            logger.console_error(f"Failed to process data: {e}", indent=4)
            return

        logger.console_print("Loading cached data...", indent=4)
        cached_data = self.load_cached_data()

        if cached_data is None:
            logger.console_info("No cached data found, initializing...", indent=4)
            self.save_data(processed_data)
            return

        logger.console_print("Comparing with cached data...", indent=4)
        try:
            changes = self.compare_data(cached_data, processed_data)
        except Exception as e:
            logger.console_error(f"Failed to compare data: {e}", indent=4)
            return

        if changes:
            change_count = len(changes) if isinstance(changes, list) else 1
            logger.console_print(f"Found {change_count} change(s), saving data...", indent=4)
            self.save_data(processed_data)
            logger.console_print("Sending notifications...", indent=4)
            try:
                self.notify_changes(changes, notifiers)
                logger.console_success("Data saved and notifications sent", indent=4)
            except Exception as e:
                logger.console_error(f"Failed to send notifications: {e}", indent=4)
        else:
            logger.console_info("No changes detected", indent=4)
            self.save_data(processed_data)

    def get_user_data_path(self, filename):
        user_dir = os.path.join(self.data_dir, self.username)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, filename)

    def load_json_file(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def save_json_file(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
