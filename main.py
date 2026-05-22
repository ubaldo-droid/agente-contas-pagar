#!/usr/bin/env python3
"""
AGENTE DE CONTAS A PAGAR
Sistema completo de gestão de contas com Gmail, Telegram e armazenamento de comprovantes

Para começar:
python main.py
"""

import os
import sys
import logging
from dotenv import load_dotenv
from database import BancoDados
from monitor_gmail import MonitorGmail
from telegram_handler import TelegramHandler
from scheduler import Agendador
import threading
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

# Configurar logging
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
        
        # Validar configurações
        self.validar_configuracao()
        
        # Inicializar componentes
        self.db = BancoDados(db_type='sqlite', db_file='contas.db')
        logger.info("✅ Banco de dados pronto")
        
        self.monitor_gmail = MonitorGmail(self.db)
        logger.info("✅ Monitor Gmail pronto")
        
        self.telegram = TelegramHandler(self.db)
        logger.info("✅ Telegram Handler pronto")
        
        self.agendador = Agendador()
        logger.info("✅ Agendador pronto")
    
    def validar_configuracao(self):
        """Valida se todas as configurações necessárias estão presentes"""
        logger.info("Validando configuração...")
        
        variaveis_obrigatorias = [
            'ANTHROPIC_API_KEY',
            'GMAIL_CREDENTIALS_FILE',
            'GMAIL_MONITORED_ADDRESS',
            'EMAIL_SENDER',
            'EMAIL_SENDER_PASSWORD',
            'EMAIL_RECIPIENT',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        faltam = []
        for var in variaveis_obrigatorias:
            if not os.getenv(var):
                faltam.append(var)
        
        if faltam:
            logger.error(f"❌ Variáveis faltando no .env:")
            for var in faltam:
                logger.error(f"   - {var}")
            logger.error("\nCopie .env.example para .env e preencha todos os campos")
            sys.exit(1)
        
        logger.info("✅ Todas as variáveis configuradas")
    
    def rodar_gmail_em_thread(self):
        """Roda Gmail em thread separada"""
        def monitor():
            logger.info("📧 Thread de monitoramento Gmail iniciada")
            try:
                while True:
                    self.monitor_gmail.monitorar_continuamente()
                    import time
                    time.sleep(1800)  # A cada 30 minutos
            except Exception as e:
                logger.error(f"❌ Erro em thread Gmail: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info("✅ Monitoramento Gmail em background")
    
    def rodar_telegram_em_thread(self):
        """Roda Telegram em thread separada"""
        def bot():
            logger.info("💬 Thread Telegram iniciada")
            try:
                self.telegram.rodar()
            except Exception as e:
                logger.error(f"❌ Erro em thread Telegram: {e}")
        
        thread = threading.Thread(target=bot, daemon=True)
        thread.start()
        logger.info("✅ Telegram rodando em background")
    
    def rodar_tudo(self):
        """Inicia todos os componentes"""
        logger.info("\n" + "=" * 60)
        logger.info("🚀 INICIANDO TODOS OS COMPONENTES")
        logger.info("=" * 60 + "\n")
        
        print("\n" + "=" * 60)
        print("🤖 AGENTE DE CONTAS A PAGAR")
        print("=" * 60)
        print(f"\n⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("\n📋 COMPONENTES ATIVOS:")
        print("  ✅ Banco de dados (SQLite)")
        print("  ✅ Monitor Gmail (a cada 30 min)")
        print("  ✅ Telegram Bot (24/7)")
        print("  ✅ Alertas diários (08:00)")
        print("\n📞 PRÓXIMOS PASSOS:")
        print("  1. Envie um email para seu rótulo 'ContasAPagar'")
        print("  2. Use /ajuda no Telegram para comandos")
        print("  3. Digite /status para verificar tudo")
        print("\n" + "=" * 60 + "\n")
        
        # Rodar Gmail em background
        self.rodar_gmail_em_thread()
        
        # Rodar Telegram em foreground (bloqueia)
        self.rodar_telegram_em_thread()
        
        # Manter aplicação rodando
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⏹️ Agente parado pelo usuário")
            print("\n⏹️ Agente finalizado. Até logo!")
            sys.exit(0)

def main():
    """Função principal"""
    try:
        # Verificar se credentials.json existe
        if not os.path.exists('credentials.json'):
            logger.warning("⚠️ credentials.json não encontrado")
            logger.warning("Para usar Gmail, faça download em:")
            logger.warning("  Google Cloud Console → APIs → Gmail → OAuth 2.0")
            logger.warning("  Salve como: credentials.json")
            response = input("\nContinuar sem Gmail? (s/n): ").lower()
            if response != 's':
                sys.exit(1)
        
        # Criar agente
        agente = AgenteCompleto()
        
        # Rodar tudo
        agente.rodar_tudo()
    
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        print(f"\n❌ Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
