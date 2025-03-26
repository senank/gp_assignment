from locust import HttpUser, task, between

from random import randint  # noqa: F401


class AppUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)  # This task runs twice as often as the other
    def qa_endpoint(self):
        """ Simulates querying the QA endpoint """
        headers = {
            "Authorization": "Bearer valid",
            "Content-Type": "application/json"
        }
        data = {"text": "What is Retrieval-Augmented Generation?"}
        # data = {"text": f"What is Retrieval-Augmented Generation?{randint(0, 100000)}"}
        self.client.post("/answer_question", json=data, headers=headers)

    @task(1)
    def upload_pdf_endpoint(self):
        """ Simulates uploading a PDF for text extraction & embedding """
        headers = {
            "Authorization": "Bearer valid",
        }
        with open("test/integration/data/add_pdf/test_add_1.pdf", 'rb') as file:
            data = {'file': ("test_add_1.pdf", file, 'application/pdf')}
            self.client.post("/add_pdf", files=data, headers=headers)
