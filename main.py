#!/usr/bin/env python3
"""
AGENTE DE CONTAS A PAGAR
Sistema completo de gestão de contas com Gmail, Telegram e armazenamento de comprovantes
"""

import os
import sys
import logging
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from database import BancoDados
from telegram_handler import TelegramHandler
from scheduler import Agendador

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agente.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AgenteCompleto:
    def __init__(self):
        logger.info("=" * 60)
        logger.info("🤖 INICIANDO AGENTE DE CONTAS A PAGAR")
        logger.info("=" * 60)

        self._validar_configuracao()

        db_file = os.getenv('DATABASE_FILE', 'contas.db')
        if os.path.dirname(db_file):
            os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db = BancoDados(db_type='sqlite', db_file=db_file)
        logger.info(f"✅ Banco de dados pronto: {db_file}")

        # Gmail monitoring é opcional — falha não derruba o sistema
        self.monitor_gmail = self._iniciar_gmail()

        self.telegram = TelegramHandler(self.db)
        logger.info("✅ Telegram Handler pronto")

        # Agendador usa o MESMO banco do Telegram
        self.agendador = Agendador(self.db)
        logger.info("✅ Agendador pronto")

    def _validar_configuracao(self):
        obrigatorias = [
            'ANTHROPIC_API_KEY',
            'EMAIL_SENDER', 'EMAIL_SENDER_PASSWORD', 'EMAIL_RECIPIENT',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
        ]
        faltam = [v for v in obrigatorias if not os.getenv(v)]
        if faltam:
            for v in faltam:
                logger.error(f"❌ Variável obrigatória ausente: {v}")
            sys.exit(1)
        logger.info("✅ Configuração validada")

    def _iniciar_gmail(self):
        """Tenta iniciar o monitor de Gmail; retorna None se não conseguir."""
        try:
            from monitor_gmail import MonitorGmail
            monitor = MonitorGmail(self.db)
            logger.info("✅ Monitor Gmail pronto")
            return monitor
        except Exception as e:
            logger.warning(f"⚠️ Monitor Gmail desativado: {e}")
            logger.warning("   Configure GMAIL_TOKEN_B64 no Render para ativar.")
            return None

    def _rodar_gmail_em_thread(self):
        if not self.monitor_gmail:
            logger.warning("⚠️ Gmail monitoring desativado — pulando thread")
            return

        def loop():
            logger.info("📧 Thread Gmail iniciada")
            while True:
                try:
                    self.monitor_gmail.monitorar_continuamente()
                except Exception as e:
                    logger.error(f"❌ Erro no ciclo Gmail: {e}")
                time.sleep(1800)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logger.info("✅ Monitor Gmail em background (a cada 30 min)")

    def _rodar_agendador_em_thread(self):
        def loop():
            logger.info("📅 Thread Agendador iniciada")
            try:
                self.agendador.agendar()
            except Exception as e:
                logger.error(f"❌ Erro no agendador: {e}", exc_info=True)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logger.info("✅ Agendador em background")

    def rodar_tudo(self):
        logger.info("🚀 INICIANDO TODOS OS COMPONENTES")
        self._rodar_gmail_em_thread()
        self._rodar_agendador_em_thread()

        logger.info("💬 Iniciando Telegram Bot no thread principal...")
        try:
            self.telegram.rodar()
        except (KeyboardInterrupt, SystemExit):
            logger.info("⏹️ Agente parado")
            sys.exit(0)


def main():
    try:
        AgenteCompleto().rodar_tudo()
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
