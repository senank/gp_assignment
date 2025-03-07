import json
import requests
import os
import pytest
from time import sleep

url = os.getenv("APP_URL", "http://localhost:8000")

answer_question_url = url + "/answer_question"
answer_question_folder = "test/data/answer_question"


class Test_AnswerQuestion:
    @classmethod
    def setup_class(cls):
        cls.url = answer_question_url
        cls.folder = answer_question_folder

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
        with open(f"{self.folder}/test_qa_1.json", 'r') as file:
            data = json.load(file)
        response = requests.post(self.url, json=data)
        print(response.json())
        assert response.status_code == 200
