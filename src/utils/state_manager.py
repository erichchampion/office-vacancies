import json
import os
import tempfile
from datetime import datetime

class StateManager:
    def __init__(self, state_path="data/state.json"):
        self.state_path = state_path

    def load_state(self):
        """Loads the state from the JSON file."""
        if not os.path.exists(self.state_path):
            return {"last_run_timestamp": None, "notified_vacancies": {}}

        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Failed to load state from {self.state_path}. Starting fresh.")
            return {"last_run_timestamp": None, "notified_vacancies": {}}

    def save_state(self, state):
        """Saves the current state to the JSON file atomically using a temporary file."""
        dir_name = os.path.dirname(self.state_path)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
            json.dump(state, tf, indent=2)
            temp_name = tf.name

        # Atomic rename ensures state is never left in a corrupted partial state
        os.replace(temp_name, self.state_path)

    def mark_notified(self, state, vacancy_id, details):
        """Updates the provided state object to mark a vacancy as notified."""
        state["notified_vacancies"][vacancy_id] = {
            "detected_at": datetime.now().isoformat(),
            "notified_at": datetime.now().isoformat(),
            **details
        }
        state["last_run_timestamp"] = datetime.now().isoformat()
        return state

    def is_notified(self, state, vacancy_id):
        """Checks if a vacancy is notified within the provided state object."""
        return vacancy_id in state["notified_vacancies"]
