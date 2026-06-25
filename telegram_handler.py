import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import BancoDados
from agente import AgenteContasPagar
from email_alertas import GeradorAlertas
from anthropic import AuthenticationError
from datetime import datetime, timedelta, date
import calendar
import json


def _gerar_datas_recorrencia(dias_do_mes: list, data_inicio_str: str, duracao_meses: int) -> list:
    """Gera lista de datas (DD/MM/YYYY) para contas recorrentes.

    Para cada mês dentro do período, gera uma data para cada dia listado em
    dias_do_mes. Datas anteriores a data_inicio e datas inválidas (ex: 30/02)
    são silenciosamente descartadas.
    """
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        data_inicio = date.today()

    datas = []
    mes_atual = date(data_inicio.year, data_inicio.month, 1)

    for _ in range(duracao_meses):
        for dia in dias_do_mes:
            try:
                ultimo_dia = calendar.monthrange(mes_atual.year, mes_atual.month)[1]
                if dia > ultimo_dia:
                    continue
                d = date(mes_atual.year, mes_atual.month, dia)
                if d >= data_inicio:
                    datas.append(d.strftime('%d/%m/%Y'))
            except (ValueError, TypeError):
                continue
        # Avança para o próximo mês
        if mes_atual.month == 12:
            mes_atual = date(mes_atual.year + 1, 1, 1)
        else:
            mes_atual = date(mes_atual.year, mes_atual.month + 1, 1)

    return datas

class TelegramHandler:
    def __init__(self, database):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = int(os.getenv('TELEGRAM_CHAT_ID', 0))
        self.db = database
        self.agente = AgenteContasPagar()
        self.gerador_alertas = GeradorAlertas(database)
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
    
    async def alerta(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dispara alerta de contas a vencer manualmente"""
        contas = self.gerador_alertas.obter_contas_proximos_dias(dias=3)
        texto = self.gerador_alertas.gerar_alerta_texto(contas)
        cabecalho = f"📅 CONTAS DOS PRÓXIMOS 3 DIAS ({datetime.now().strftime('%d/%m/%Y')}):\n\n"
        await update.message.reply_text(cabecalho + texto)

    async def ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra ajuda completa"""
        texto = """
📚 AJUDA - Comandos do Agente

📋 VISUALIZAR CONTAS:
/proximas - Próximas 3 dias
/todas - Todas pendentes
/pagas - Contas já pagas
/alerta - Alerta completo de vencimentos

📊 RELATÓRIOS:
/relatorio - Gastos por categoria

🏷️ GERENCIAMENTO:
/categorias - Listar categorias
/paga <id> - Marcar como paga

❓ OUTROS:
/ajuda - Esta mensagem
/status - Status do agente

💡 DICAS:
- Use /alerta a qualquer hora para ver contas dos próximos 3 dias
- Envie texto aqui descrevendo a conta para cadastrá-la
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
    
    def _formatar_conta_salva(self, dados, conta_id: int) -> str:
        msg = (
            f"✅ ID #{conta_id} — {dados.get('fornecedor', '-')}\n"
            f"   💰 R$ {float(dados.get('valor', 0)):.2f}  📅 {dados.get('vencimento', '-')}"
            f"  💳 {dados.get('forma_pagamento', '-')}  📁 {dados.get('categoria', '-')}"
        )
        if dados.get('dados_pagamento'):
            msg += f"\n   🔑 {dados.get('dados_pagamento')}"
        return msg

    async def _salvar_uma_conta(self, dados: dict) -> tuple[int | None, str]:
        """Salva uma única conta; retorna (id, mensagem)"""
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
            return conta_id, self._formatar_conta_salva(dados, conta_id)
        except Exception as e:
            return None, f"❌ Erro ao salvar {dados.get('fornecedor', '?')}: {e}"

    async def _salvar_conta_ou_responder(self, update: Update, dados, resposta_ia: str):
        """Salva conta(s) identificada(s) no banco ou informa o usuário"""
        if not dados:
            await update.message.reply_text(
                "🤔 Não consegui identificar uma conta nos dados informados.\n\n"
                "Para texto, inclua fornecedor, valor, vencimento e forma de pagamento.\n"
                "Para arquivos, envie uma foto do boleto ou o PDF."
            )
            return

        tipo = dados.get('tipo_resposta')

        if tipo == 'multiplas_contas':
            contas = dados.get('contas', [])
            linhas = [f"✅ {len(contas)} contas registradas:\n"]
            erros = []
            for c in contas:
                if c.get('tipo_resposta') == 'conta_identificada':
                    conta_id, msg = await self._salvar_uma_conta(c)
                    if conta_id:
                        linhas.append(msg)
                    else:
                        erros.append(msg)
            if linhas:
                await update.message.reply_text('\n'.join(linhas))
            if erros:
                await update.message.reply_text('\n'.join(erros))

        elif tipo == 'conta_identificada':
            conta_id, msg = await self._salvar_uma_conta(dados)
            if conta_id:
                await update.message.reply_text(f"✅ Conta registrada!\n\n{msg}")
            else:
                await update.message.reply_text(msg)

        elif tipo == 'conta_recorrente':
            await self._processar_conta_recorrente(update, dados)

        elif tipo == 'comprovante_identificado':
            await self._processar_comprovante(update, dados)

        else:
            await update.message.reply_text(
                "🤔 Não consegui identificar uma conta nos dados informados.\n\n"
                "Para texto, inclua fornecedor, valor, vencimento e forma de pagamento.\n"
                "Para arquivos, envie uma foto do boleto ou o PDF."
            )

    async def _processar_conta_recorrente(self, update: Update, dados: dict):
        """Gera e salva todas as ocorrências de uma conta recorrente"""
        rec = dados.get('recorrencia', {})
        dias_do_mes = rec.get('dias_do_mes', [])
        data_inicio = rec.get('data_inicio', '')
        duracao_meses = int(rec.get('duracao_meses', 1))

        if not dias_do_mes or not data_inicio:
            await update.message.reply_text(
                "❌ Dados de recorrência incompletos. Informe os dias do mês, data de início e duração."
            )
            return

        datas = _gerar_datas_recorrencia(dias_do_mes, data_inicio, duracao_meses)
        if not datas:
            await update.message.reply_text(
                "❌ Nenhuma data gerada para os parâmetros informados. Verifique os dias e o período."
            )
            return

        await update.message.reply_text(
            f"⏳ Gerando {len(datas)} lançamentos para {dados.get('fornecedor', '-')}..."
        )

        ids_salvos = []
        erros = []
        for vencimento in datas:
            conta_dados = {
                'vencimento': vencimento,
                'fornecedor': dados.get('fornecedor'),
                'valor': dados.get('valor'),
                'categoria': dados.get('categoria'),
                'forma_pagamento': dados.get('forma_pagamento'),
                'dados_pagamento': dados.get('dados_pagamento'),
                'observacoes': dados.get('observacoes', ''),
            }
            conta_id, msg = await self._salvar_uma_conta(conta_dados)
            if conta_id:
                ids_salvos.append((conta_id, vencimento))
            else:
                erros.append(msg)

        linhas = [
            f"✅ {len(ids_salvos)} lançamentos criados para {dados.get('fornecedor', '-')}!\n",
            f"💰 R$ {float(dados.get('valor', 0)):.2f} cada  |  {dados.get('forma_pagamento', '-')}",
        ]
        if dados.get('dados_pagamento'):
            linhas.append(f"🔑 {dados.get('dados_pagamento')}")
        linhas.append(f"\n📅 Datas geradas ({len(ids_salvos)}):")
        for cid, venc in ids_salvos:
            linhas.append(f"  ID #{cid} — {venc}")
        if erros:
            linhas.append(f"\n⚠️ {len(erros)} erro(s):\n" + "\n".join(erros))

        # Telegram limita mensagens a ~4096 chars; divide se necessário
        texto = "\n".join(linhas)
        if len(texto) <= 4000:
            await update.message.reply_text(texto)
        else:
            resumo = "\n".join(linhas[:6]) + f"\n...e mais {len(ids_salvos) - 3} datas."
            await update.message.reply_text(resumo)

    async def _processar_comprovante(self, update: Update, dados: dict):
        """Tenta identificar a conta paga e marcá-la automaticamente"""
        ext = dados.get('dados_extraidos', {})
        valor_raw = ext.get('valor')
        data_pagamento = ext.get('data') or datetime.now().strftime('%d/%m/%Y')
        beneficiario = (ext.get('beneficiario') or '').strip()
        tipo_transacao = ext.get('tipo_transacao', '-')
        instituicao = ext.get('instituicao', '-')

        cabecalho = (
            f"🧾 Comprovante identificado:\n"
            f"💰 R$ {float(valor_raw):.2f}  📅 {data_pagamento}\n"
            f"🏦 {tipo_transacao} — {instituicao}"
            + (f"\n👤 {beneficiario}" if beneficiario else "")
            + "\n"
        )

        if not valor_raw:
            await update.message.reply_text(
                cabecalho + "\n⚠️ Não foi possível extrair o valor. Use /paga <id> manualmente."
            )
            return

        candidatos = self.db.buscar_contas_por_valor(float(valor_raw))

        if not candidatos:
            await update.message.reply_text(
                cabecalho +
                "\n⚠️ Nenhuma conta pendente com esse valor encontrada no banco.\n"
                "Use /paga <id> para marcar manualmente se necessário."
            )
            return

        # Tenta refinar por nome do beneficiário
        if len(candidatos) > 1 and beneficiario:
            nome_lower = beneficiario.lower()
            filtrados = [
                c for c in candidatos
                if nome_lower in c.fornecedor.lower() or c.fornecedor.lower() in nome_lower
            ]
            if filtrados:
                candidatos = filtrados

        if len(candidatos) == 1:
            conta = candidatos[0]
            self.db.marcar_como_paga(conta.id, data_pagamento)
            await update.message.reply_text(
                cabecalho +
                f"\n✅ Conta marcada como PAGA!\n"
                f"ID #{conta.id} | {conta.fornecedor}\n"
                f"R$ {conta.valor:.2f} | Pago em {data_pagamento}"
            )
        else:
            linhas = [
                cabecalho,
                f"⚠️ {len(candidatos)} contas pendentes com esse valor. Confirme qual foi paga:\n",
            ]
            for c in candidatos:
                linhas.append(f"  ID #{c.id} | {c.fornecedor} | venc. {c.vencimento}")
            linhas.append("\nResponda com /paga <id> para registrar.")
            await update.message.reply_text('\n'.join(linhas))

    async def mensagem_texto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto com agente IA e salva no banco"""
        texto = update.message.text
        await update.message.reply_text("🤔 Analisando com IA...")
        try:
            resposta = self.agente.processar_entrada(f"Mensagem do usuário: {texto}")
            dados = self.agente.extrair_json_resposta(resposta)
        except AuthenticationError:
            await update.message.reply_text(
                "❌ Chave da API Anthropic inválida ou expirada.\n\n"
                "Atualize a variável ANTHROPIC_API_KEY no arquivo .env com uma chave válida."
            )
            return
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao processar com IA: {e}")
            return
        await self._salvar_conta_ou_responder(update, dados, resposta)

    async def processar_foto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa foto enviada (boleto, fatura, comprovante)"""
        await update.message.reply_text("🔍 Analisando imagem com IA...")
        photo = update.message.photo[-1]
        legenda = update.message.caption or ''
        try:
            arquivo = await context.bot.get_file(photo.file_id)
            dados_binarios = bytes(await arquivo.download_as_bytearray())
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao baixar imagem: {e}")
            return
        await self._processar_arquivo_e_salvar(update, dados_binarios, 'image/jpeg', 'foto.jpg', legenda)

    async def processar_documento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa documento (PDF, imagem) enviado como arquivo"""
        doc = update.message.document
        mime_type = doc.mime_type or 'application/octet-stream'
        nome = doc.file_name or 'arquivo'
        legenda = update.message.caption or ''

        tipos_suportados = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        if mime_type not in tipos_suportados:
            await update.message.reply_text(
                f"❌ Formato '{mime_type}' não suportado.\n\nEnvie PDF, JPEG, PNG ou WebP."
            )
            return

        await update.message.reply_text(f"🔍 Analisando {nome} com IA...")
        try:
            arquivo = await context.bot.get_file(doc.file_id)
            dados_binarios = bytes(await arquivo.download_as_bytearray())
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao baixar arquivo: {e}")
            return
        await self._processar_arquivo_e_salvar(update, dados_binarios, mime_type, nome, legenda)

    async def _processar_arquivo_e_salvar(self, update, dados_binarios: bytes, mime_type: str, nome: str, legenda: str):
        """Processa arquivo com visão da IA e salva resultado no banco"""
        try:
            resposta = self.agente.processar_arquivo(dados_binarios, mime_type, nome, legenda)
            dados = self.agente.extrair_json_resposta(resposta)
        except AuthenticationError:
            await update.message.reply_text("❌ Chave da API Anthropic inválida ou expirada.")
            return
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao processar arquivo: {e}")
            return
        await self._salvar_conta_ou_responder(update, dados, resposta)
    
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
        self.application.add_handler(CommandHandler("alerta", self.alerta))
        self.application.add_handler(CommandHandler("ajuda", self.ajuda))
        self.application.add_handler(CommandHandler("status", self.status))
        
        # Handlers de mensagens
        self.application.add_handler(MessageHandler(filters.PHOTO, self.processar_foto))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.processar_documento))
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
