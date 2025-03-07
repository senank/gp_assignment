import json
import requests
import os

url = os.getenv("APP_URL", "http://localhost:8000")

answer_question_url = url + "/answer_question"
answer_question_folder = "test/data/answer_question"


class Test_AnswerQuestion:
    @classmethod
    def setup_class(cls):
        cls.url = answer_question_url
        cls.folder = answer_question_folder

    def test_valid(self):
        with open(f"{self.folder}/test_qa_1.json", 'r') as file:
            data = json.load(file)
        response = requests.post(self.url, json=data)
        print(response.json())
        assert response.status_code == 200