from locust import HttpUser, task, between


class CleairB2CUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        res = self.client.post("/v1/session")
        if res.status_code == 200:
            self.token = res.json().get("session_token", "")
        else:
            self.token = ""

    @task(3)
    def get_air_current(self):
        self.client.get("/v1/air/current?lat=19.076&lon=72.8777")

    @task(2)
    def get_air_forecast(self):
        self.client.get("/v1/air/forecast?lat=19.076&lon=72.8777")

    @task(1)
    def get_health(self):
        self.client.get("/v1/health")
