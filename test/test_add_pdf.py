import requests
import os

url = os.getenv("APP_URL", "http://localhost:8000")

add_pdf_url = url + "/add_pdf"
add_pdf_folder = "test/data/add_pdf"


class Test_AddPDF:
    @classmethod
    def setup_class(cls):
        cls.url = add_pdf_url
        cls.folder = add_pdf_folder

    def test_valid(self):
        with open(f"{self.folder}/test_add_1.pdf", 'rb') as file:
            data = {'file': ("test_add_1.pdf", file, 'application/pdf')}
            response = requests.post(self.url, files=data)
            print(response.json())
            assert response.status_code == 200
