import re

class VacancyEngine:
    def __init__(self, config):
        self.matrix = config["eligibility_matrix"]

    def _extract_number(self, text):
        """Extracts the most likely count from a string (usually the last number)."""
        if not text:
            return 0
        numbers = re.findall(r'\d+', str(text))
        return int(numbers[-1]) if numbers else 0

    def check_eligibility(self, office_name):
        """Returns the Tier if eligible, otherwise None."""
        for tier, data in self.matrix.items():
            for eligible_office in data["offices"]:
                if eligible_office.lower() in office_name.lower():
                    return tier
        return None

    def process_candidate_data(self, scraped_rows):
        """
        scraped_rows: List of tuples (office_name, seats_open, candidates_filed)
        """
        alerts = []
        for office, open_seats, filed in scraped_rows:
            tier = self.check_eligibility(office)
            if tier:
                open_val = self._extract_number(open_seats)
                filed_val = self._extract_number(filed)

                if filed_val < open_val:
                    alerts.append({
                        "office": office,
                        "vacancies": open_val - filed_val,
                        "tier": f"{tier}: {self.matrix[tier]['description']}",
                        "urgency": "HIGH",
                        "link": "https://votescount.santacruzcountyca.gov"
                    })
        return alerts
