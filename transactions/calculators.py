# Calculateurs pour int�r�ts, renflouement, etc.

from django.apps import AppConfig

class TonAppConfig(AppConfig):
    name = 'core'

    def ready(self):
        import core.signals  # Charge les signals