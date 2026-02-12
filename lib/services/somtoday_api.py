import requests


class SomTodayAPI:
    def __init__(self, api_base, oauth_url, client_id, pagination_size=100, timeout=30):
        self.api_base = api_base
        self.oauth_url = oauth_url
        self.client_id = client_id
        self.pagination_size = pagination_size
        self.timeout = timeout

    def refresh_token(self, refresh_token):
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        response = requests.post(self.oauth_url, data=data, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        access_token = result["access_token"]
        new_refresh_token = result.get("refresh_token", refresh_token)

        return access_token, new_refresh_token

    def fetch_grades(self, access_token, leerling_id):
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        params = {
            "type": [
                "Toetskolom",
                "DeeltoetsKolom",
                "Werkstukcijferkolom",
                "Advieskolom",
            ],
            "additional": [
                "vaknaam",
                "resultaatkolom",
                "naamalternatiefniveau",
                "vakuuid",
                "lichtinguuid",
            ],
            "sort": "desc-geldendResultaatCijferInvoer",
        }

        all_grades = []

        endpoints = [
            f"{self.api_base}/geldendvoortgangsdossierresultaten/leerling/{leerling_id}",
            f"{self.api_base}/geldendexamendossierresultaten/leerling/{leerling_id}",
        ]

        for url in endpoints:
            range_start = 0
            range_size = self.pagination_size

            while True:
                headers["Range"] = f"items={range_start}-{range_start + range_size - 1}"
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()

                batch = response.json().get("items", [])
                if not batch:
                    break

                all_grades.extend(batch)
                range_start += range_size

                if len(batch) < range_size:
                    break

        return all_grades

    def fetch_schedule(self, access_token, start_date, end_date):
        url = f"{self.api_base}/afspraken"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        params = {"begindatum": start_date, "einddatum": end_date}

        response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()

        return response.json().get("items", [])

    def fetch_subjects(self, access_token):
        url = f"{self.api_base}/vakken"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        return response.json().get("items", [])
