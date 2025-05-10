from locust import HttpUser, task, between
import random
import string

class RecommendationUser(HttpUser):
    wait_time = between(0.5, 2)  # Pausa entre requisições

    def on_start(self):
        # Gera um perfil único para cada usuário simulado
        self.profile_hash = "dashboard"
        self.tenant_id = "1tenant_123"  # Altere conforme necessário

    @task
    def get_recommendation_and_click(self):
        # Passo 1: Obter recomendação
        with self.client.get(
            f"/recommendation?tenant_id={self.tenant_id}&profile_hash={self.profile_hash}",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure("Erro ao obter recomendação")
                return

            try:
                recommendation = response.json()
                arm_id = recommendation['arm_id']
            except (KeyError, ValueError):
                response.failure("Formato inválido da resposta")
                return

        # Passo 2: Registrar clique
        click_data = {
            "tenant_id": self.tenant_id,
            "profile_hash": self.profile_hash,
            "arm_id": arm_id,
            "clicked": True
        }

        with self.client.post("/click", json=click_data, catch_response=True) as click_response:
            if click_response.status_code != 200:
                click_response.failure("Erro ao registrar clique")