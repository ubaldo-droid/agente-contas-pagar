from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os
from database import BancoDados
from monitor_gmail import MonitorGmail
from email_alertas import GeradorAlertas
from datetime import datetime
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Agendador:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db = BancoDados(db_type='sqlite', db_file='contas.db')
        self.monitor = MonitorGmail(self.db)
        self.gerador_alertas = GeradorAlertas(self.db)
        self.timezone = pytz.timezone(os.getenv('ALERTA_TIMEZONE', 'America/Sao_Paulo'))
    
    def tarefa_monitorar_gmail(self):
        """Executa monitoramento de Gmail"""
        try:
            logger.info("⏰ Executando monitoramento de Gmail...")
            self.monitor.monitorar_continuamente()
            logger.info("✅ Monitoramento concluído")
        except Exception as e:
            logger.error(f"❌ Erro no monitoramento: {e}")
    
    def tarefa_alerta_diario(self):
        """Executa alerta diário"""
        try:
            logger.info("⏰ Enviando alerta diário...")
            self.gerador_alertas.enviar_email_alerta()
            logger.info("✅ Alerta enviado")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar alerta: {e}")
    
    def agendar(self):
        """Configura agendamento de tarefas"""
        
        # Monitorar Gmail a cada 30 minutos
        self.scheduler.add_job(
            self.tarefa_monitorar_gmail,
            'interval',
            minutes=30,
            id='monitor_gmail'
        )
        logger.info("📧 Monitoramento Gmail agendado a cada 30 minutos")
        
        # Alerta diário às 8h da manhã
        if os.getenv('ALERTA_DIARIO', 'True') == 'True':
            hora = int(os.getenv('ALERTA_HORA', 8))
            minuto = int(os.getenv('ALERTA_MINUTO', 0))
            
            self.scheduler.add_job(
                self.tarefa_alerta_diario,
                CronTrigger(hour=hora, minute=minuto, timezone=self.timezone),
                id='alerta_diario'
            )
            logger.info(f"📬 Alerta diário agendado para {hora:02d}:{minuto:02d}")
        
        self.scheduler.start()
        logger.info("✅ Agendador iniciado!")
        
        try:
            # Bloqueia enquanto o scheduler está rodando
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️ Agendador parado pelo usuário")
            self.scheduler.shutdown()

if __name__ == '__main__':
    agendador = Agendador()
    agendador.agendar()
