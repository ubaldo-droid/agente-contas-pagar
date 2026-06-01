from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os
from email_alertas import GeradorAlertas
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class Agendador:
    def __init__(self, database):
        self.scheduler = BackgroundScheduler()
        self.db = database
        self.gerador_alertas = GeradorAlertas(self.db)
        self.timezone = pytz.timezone(os.getenv('ALERTA_TIMEZONE', 'America/Sao_Paulo'))

    def tarefa_alerta_diario(self):
        """Executa alerta diário via email e Telegram"""
        try:
            logger.info("⏰ Disparando alerta diário...")
            contas = self.gerador_alertas.obter_contas_proximos_dias(dias=3)
            logger.info(f"📊 Contas encontradas para alerta: {len(contas)}")
            for c in contas:
                logger.info(f"   → {c['fornecedor']} | R${c['valor']:.2f} | vence {c['vencimento']}")
            self.gerador_alertas.enviar_alertas_diarios()
            logger.info("✅ Alerta diário enviado")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar alerta: {e}", exc_info=True)

    def agendar(self):
        """Configura agendamento de tarefas"""
        if os.getenv('ALERTA_DIARIO', 'True') == 'True':
            hora = int(os.getenv('ALERTA_HORA', 8))
            minuto = int(os.getenv('ALERTA_MINUTO', 0))

            self.scheduler.add_job(
                self.tarefa_alerta_diario,
                CronTrigger(hour=hora, minute=minuto, timezone=self.timezone),
                id='alerta_diario'
            )
            logger.info(f"📬 Alerta diário agendado para {hora:02d}:{minuto:02d} ({self.timezone})")

        self.scheduler.start()
        logger.info("✅ Agendador iniciado!")
