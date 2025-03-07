import requests
import os
import pytest
from time import sleep

url = os.getenv("APP_URL", "http://localhost:8000")

add_pdf_url = url + "/add_pdf"
add_pdf_folder = "test/data/add_pdf"


class Test_AddPDF:
    @classmethod
    def setup_class(cls):
        cls.url = add_pdf_url
        cls.folder = add_pdf_folder

    @pytest.fixture(autouse=True)
    def wait_for_service(self):
        """Waits for the service to be available before running tests"""
        max_retries = 5
        delay = 3  # seconds
        for attempt in range(max_retries):
            try:
                response = requests.get(url + "/")
                if response.status_code == 200:
                    print("Service is up!")
                    return
            except requests.exceptions.RequestException:
                pass
            print(f"Service not available yet, retrying ({attempt + 1}/{max_retries})...")  # noqa: E501
            sleep(delay)
        pytest.fail("Service failed to start after multiple retries")

    def test_valid(self):
        with open(f"{self.folder}/test_add_1.pdf", 'rb') as file:
            data = {'file': ("test_add_1.pdf", file, 'application/pdf')}
            response = requests.post(self.url, files=data)
            print(response.json())
            assert response.status_code == 200
