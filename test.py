from seleniumwire import webdriver
from seleniumbase import BaseCase


BaseCase.main(__name__, __file__)

class BaseTestCase(BaseCase):
    def setUp(self):
        super().setUp()
        self.driver.close()
        self.driver = webdriver.Chrome()

    def test_wire(self):
        self.open('https://seleniumbase.io/w3schools/')

        for request in self.driver.requests:
            if request.response:
                print(
                    request.url,
                    request.response.status_code,
                    request.response.headers['Content-Type']
                )