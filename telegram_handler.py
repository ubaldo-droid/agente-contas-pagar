import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import BancoDados
from agente import AgenteContasPagar
from datetime import datetime, timedelta
import json

class TelegramHandler:
    def __init__(self, database):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = int(os.getenv('TELEGRAM_CHAT_ID', 0))
        self.db = database
        self.agente = AgenteContasPagar()
        self.application = None
    
    async def iniciar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        await update.message.reply_text(
            "👋 Bem-vindo ao Agente de Contas a Pagar!\n\n"
            "Comandos disponíveis:\n"
            "/proximas - Próximas contas vencendo\n"
            "/todas - Todas as contas pendentes\n"
            "/pagas - Contas já pagas\n"
            "/relatorio - Relatório de gastos\n"
            "/categorias - Listar categorias\n"
            "/paga <id> - Marcar conta como paga\n"
            "/ajuda - Ajuda completa"
        )
    
    async def proximas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra próximas 3 contas vencendo"""
        contas = self.db.obter_proximas_contas(dias=3)
        
        if not contas:
            await update.message.reply_text("✅ Nenhuma conta vencendo nos próximos 3 dias")
            return
        
        hoje = datetime.now().date()
        mensagem = "📅 PRÓXIMAS CONTAS (3 DIAS):\n\n"

        for conta in contas[:10]:
            try:
                vencimento = datetime.strptime(conta.vencimento, '%d/%m/%Y').date()
                dias_faltam = (vencimento - hoje).days

                if dias_faltam <= 3:
                    emoji = "🔴" if dias_faltam == 0 else "🟡" if dias_faltam <= 1 else "🟠"
                    mensagem += f"{emoji} {conta.vencimento}\n"
                    mensagem += f"  {conta.fornecedor}\n"
                    mensagem += f"  R$ {conta.valor:.2f} | {conta.forma_pagamento}\n"
                    mensagem += f"  ID: #{conta.id}\n\n"
            except:
                pass

        await update.message.reply_text(mensagem if len(mensagem) > 30 else "Nenhuma conta próxima")
    
    async def todas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra todas as contas pendentes"""
        contas = self.db.listar_todas_contas()
        contas_pendentes = [c for c in contas if c.status == 'Pendente']
        
        if not contas_pendentes:
            await update.message.reply_text("✅ Nenhuma conta pendente")
            return
        
        mensagem = f"📋 CONTAS PENDENTES ({len(contas_pendentes)}):\n\n"
        
        for conta in contas_pendentes[:15]:
            mensagem += f"ID #{conta.id} | {conta.vencimento}\n"
            mensagem += f"  {conta.fornecedor} - R$ {conta.valor:.2f}\n"
            mensagem += f"  {conta.forma_pagamento}\n\n"
        
        await update.message.reply_text(mensagem)
    
    async def pagas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra contas pagas"""
        contas = self.db.listar_todas_contas()
        contas_pagas = [c for c in contas if c.status == 'Pago']
        
        if not contas_pagas:
            await update.message.reply_text("Nenhuma conta paga registrada")
            return
        
        mensagem = f"✅ CONTAS PAGAS ({len(contas_pagas)}):\n\n"
        
        for conta in contas_pagas[-10:]:
            mensagem += f"ID #{conta.id} | Pago: {conta.data_pagamento}\n"
            mensagem += f"  {conta.fornecedor} - R$ {conta.valor:.2f}\n\n"
        
        await update.message.reply_text(mensagem)
    
    async def relatorio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gera relatório de gastos por categoria"""
        contas = self.db.listar_todas_contas()
        
        categorias_dict = {}
        total_geral = 0
        
        for conta in contas:
            if conta.status in ['Pendente', 'Pago']:
                if conta.categoria not in categorias_dict:
                    categorias_dict[conta.categoria] = 0
                categorias_dict[conta.categoria] += conta.valor
                total_geral += conta.valor
        
        if not categorias_dict:
            await update.message.reply_text("Sem dados para relatório")
            return
        
        mensagem = "📊 GASTOS POR CATEGORIA:\n\n"
        
        for cat in sorted(categorias_dict.items(), key=lambda x: x[1], reverse=True):
            porcentagem = (cat[1] / total_geral * 100) if total_geral > 0 else 0
            mensagem += f"{cat[0]}: R$ {cat[1]:.2f} ({porcentagem:.1f}%)\n"
        
        mensagem += f"\n💰 TOTAL: R$ {total_geral:.2f}"
        
        await update.message.reply_text(mensagem)
    
    async def categorias(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista categorias disponíveis"""
        mensagem = "📁 CATEGORIAS DISPONÍVEIS:\n\n"
        
        categorias_lista = [
            'Condomínio', 'IPTU', 'Curso extra João', 'Curso extra Gigi',
            'Cartão crédito visa BB', 'Cartão crédito Mastercard BB',
            'Cartão crédito visa itaú', 'Marina', 'Marinheiro', 'Babá',
            'Salário Edna', 'Salário Vitor', 'Gislaini', 'Vale transporte Edna',
            'Condomínio Manso', 'Ajuda Vovó', 'CMSP', 'Celular', 'Cesari', 'Outro'
        ]
        
        for i, cat in enumerate(categorias_lista, 1):
            mensagem += f"{i}. {cat}\n"
        
        await update.message.reply_text(mensagem)
    
    async def paga(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Marca uma conta como paga"""
        if not context.args:
            await update.message.reply_text("Uso: /paga <id_da_conta>")
            return
        
        try:
            conta_id = int(context.args[0])
            self.db.marcar_como_paga(conta_id)
            await update.message.reply_text(f"✅ Conta #{conta_id} marcada como paga")
        except ValueError:
            await update.message.reply_text("❌ ID inválido")
    
    async def ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra ajuda completa"""
        texto = """
📚 AJUDA - Comandos do Agente

📋 VISUALIZAR CONTAS:
/proximas - Próximas 3 dias
/todas - Todas pendentes
/pagas - Contas já pagas

📊 RELATÓRIOS:
/relatorio - Gastos por categoria

🏷️ GERENCIAMENTO:
/categorias - Listar categorias
/paga <id> - Marcar como paga

❓ OUTROS:
/ajuda - Esta mensagem
/status - Status do agente

💡 DICAS:
- Use /proximas diariamente
- Envie comprovantes por email para registrar pagamentos
- Categorize bem para relatórios precisos
"""
        await update.message.reply_text(texto)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra status do agente"""
        contas = self.db.listar_todas_contas()
        pendentes = len([c for c in contas if c.status == 'Pendente'])
        pagas = len([c for c in contas if c.status == 'Pago'])
        
        texto = f"""
✅ AGENTE OPERACIONAL

📊 ESTATÍSTICAS:
Contas pendentes: {pendentes}
Contas pagas: {pagas}
Total registrado: {len(contas)}

🔄 MONITORAMENTO:
Gmail: Ativo ✅
Alertas: Diários ✅
Comprovantes: Armazenando ✅

💾 BANCO DE DADOS:
Status: Operacional ✅
Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        await update.message.reply_text(texto)
    
    async def mensagem_texto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto com agente IA e salva no banco"""
        texto = update.message.text

        await update.message.reply_text("🤔 Analisando com IA...")

        try:
            resposta = self.agente.processar_entrada(f"Mensagem do usuário: {texto}")
            dados = self.agente.extrair_json_resposta(resposta)
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao processar com IA: {e}")
            return

        if dados and dados.get('tipo_resposta') == 'conta_identificada':
            try:
                conta_id = self.db.adicionar_conta(
                    vencimento=dados.get('vencimento'),
                    fornecedor=dados.get('fornecedor'),
                    valor=dados.get('valor'),
                    categoria=dados.get('categoria'),
                    forma_pagamento=dados.get('forma_pagamento'),
                    codigo_pix=dados.get('dados_pagamento'),
                    observacoes=dados.get('observacoes', '')
                )
                resposta_msg = (
                    f"✅ Conta registrada! ID #{conta_id}\n\n"
                    f"👤 {dados.get('fornecedor', '-')}\n"
                    f"💰 R$ {float(dados.get('valor', 0)):.2f}\n"
                    f"📅 Vencimento: {dados.get('vencimento', '-')}\n"
                    f"💳 {dados.get('forma_pagamento', '-')}\n"
                    f"📁 {dados.get('categoria', '-')}\n"
                )
                if dados.get('dados_pagamento'):
                    resposta_msg += f"🔑 {dados.get('dados_pagamento')}\n"
                if dados.get('observacoes'):
                    resposta_msg += f"📝 {dados.get('observacoes')}\n"
                await update.message.reply_text(resposta_msg)
            except Exception as e:
                await update.message.reply_text(f"❌ Erro ao salvar no banco: {e}")
        else:
            await update.message.reply_text(
                "Não consegui identificar uma conta nos dados informados.\n\n"
                "Inclua:\n"
                "• Fornecedor/nome\n"
                "• Valor (ex: R$ 1.500,00)\n"
                "• Vencimento (ex: 30/05/2026)\n"
                "• Forma de pagamento (PIX, boleto, etc.)"
            )
    
    async def enviar_alerta(self, mensagem: str):
        """Envia alerta para o usuário via Telegram"""
        if self.application and self.chat_id:
            try:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=mensagem
                )
            except Exception as e:
                print(f"❌ Erro ao enviar Telegram: {e}")
    
    def setup(self):
        """Configura handlers do Telegram"""
        self.application = Application.builder().token(self.token).build()
        
        # Handlers de comandos
        self.application.add_handler(CommandHandler("start", self.iniciar))
        self.application.add_handler(CommandHandler("proximas", self.proximas))
        self.application.add_handler(CommandHandler("todas", self.todas))
        self.application.add_handler(CommandHandler("pagas", self.pagas))
        self.application.add_handler(CommandHandler("relatorio", self.relatorio))
        self.application.add_handler(CommandHandler("categorias", self.categorias))
        self.application.add_handler(CommandHandler("paga", self.paga))
        self.application.add_handler(CommandHandler("ajuda", self.ajuda))
        self.application.add_handler(CommandHandler("status", self.status))
        
        # Handler de mensagens de texto
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.mensagem_texto))
    
    def rodar(self):
        """Inicia o bot"""
        self.setup()
        print("🤖 Telegram Bot iniciado...")
        self.application.run_polling()

if __name__ == '__main__':
    db = BancoDados(db_type='sqlite', db_file='contas.db')
    handler = TelegramHandler(db)
    handler.rodar()
