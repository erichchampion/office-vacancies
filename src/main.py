import hashlib
import json
import os
from datetime import datetime
from src.collectors.collector_nominations import NominationCollector
from src.collectors.collector_notices import NoticeCollector
from src.engine.vacancy_engine import VacancyEngine
from src.utils.notifier import Notifier
from src.utils.state_manager import StateManager

def load_config():
    with open("config/config.json", "r") as f:
        return json.load(f)

def generate_id(text):
    """Generates a stable, deterministic hash for a string."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]

def main():
    config = load_config()
    state_mgr = StateManager()
    engine = VacancyEngine(config)
    notifier = Notifier(config)

    # Load state once at the beginning to avoid redundant disk I/O
    state = state_mgr.load_state()

    print(f"--- Starting Vacancy Check: {datetime.now()} ---")

    # 1. Nomination Check (Seasonal)
    # Logic: Only run during Jan-Feb or July-Aug
    month = datetime.now().month
    if month in [1, 2, 7, 8]:
        print("Running nomination collection...")
        nom_collector = NominationCollector(config)
        nom_data = nom_collector.collect()
        vacancies = engine.process_candidate_data(nom_data)

        for v in vacancies:
            # Create a stable unique ID for the vacancy (Office + Year)
            v_id = generate_id(f"{v['office']}_{datetime.now().year}")
            if not state_mgr.is_notified(state, v_id):
                notifier.send_alert(v)
                state = state_mgr.mark_notified(state, v_id, v)
    else:
        print("Skipping nominations (outside window).")

    # 2. Notice Check (Year-round)
    print("Running notice collection...")
    notice_collector = NoticeCollector(config)
    notices = notice_collector.collect()

    for n in notices:
        # Unique ID based on URL using stable hash
        n_id = f"notice_{generate_id(n['link'])}"
        if not state_mgr.is_notified(state, n_id):
            # Transform notice to alert format
            alert = {
                "office": n["text"],
                "vacancies": 1,
                "tier": n["tier"],
                "urgency": "MEDIUM",
                "link": n["link"]
            }
            notifier.send_alert(alert)
            state = state_mgr.mark_notified(state, n_id, n)

    # Save state once at the end
    state_mgr.save_state(state)
    print("--- Check Completed ---")

if __name__ == "__main__":
    main()
