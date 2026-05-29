import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from database import BancoDados
import os
import requests

class GeradorAlertas:
    def __init__(self, database):
        self.db = database
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.sender = os.getenv('EMAIL_SENDER')
        self.senha = os.getenv('EMAIL_SENDER_PASSWORD')
        self.destinatario = os.getenv('EMAIL_RECIPIENT')
    
    def obter_contas_proximos_dias(self, dias=3):
        """Busca contas que vencerão nos próximos dias"""
        contas = self.db.obter_proximas_contas(dias=dias)
        
        hoje = datetime.now().date()
        contas_filtradas = []
        
        for conta in contas:
            try:
                vencimento = datetime.strptime(conta.vencimento, '%d/%m/%Y').date()
                dias_faltam = (vencimento - hoje).days
                
                if 0 <= dias_faltam <= dias:
                    contas_filtradas.append({
                        'id': conta.id,
                        'fornecedor': conta.fornecedor,
                        'valor': conta.valor,
                        'vencimento': conta.vencimento,
                        'forma_pagamento': conta.forma_pagamento,
                        'dados_pagamento': conta.codigo_pix_conta,
                        'dias_faltam': dias_faltam
                    })
            except:
                pass
        
        # Ordena por dias faltantes
        contas_filtradas.sort(key=lambda x: x['dias_faltam'])
        
        return contas_filtradas
    
    def gerar_html_alerta(self, contas):
        """Gera HTML do email de alerta"""
        html = """
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .header {
                    border-bottom: 3px solid #2c3e50;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }
                .header h1 {
                    color: #2c3e50;
                    margin: 0;
                    font-size: 24px;
                }
                .header p {
                    color: #7f8c8d;
                    margin: 5px 0 0 0;
                    font-size: 14px;
                }
                .conta-item {
                    border-left: 4px solid #e74c3c;
                    padding: 15px;
                    margin: 15px 0;
                    background-color: #fafafa;
                    border-radius: 4px;
                }
                .conta-item.proximo {
                    border-left-color: #e67e22;
                }
                .conta-item.hoje {
                    border-left-color: #c0392b;
                    background-color: #fff5f5;
                }
                .fornecedor {
                    font-weight: bold;
                    font-size: 16px;
                    color: #2c3e50;
                    margin: 0 0 10px 0;
                }
                .dados {
                    font-size: 13px;
                    color: #34495e;
                    margin: 5px 0;
                }
                .valor {
                    font-size: 18px;
                    font-weight: bold;
                    color: #e74c3c;
                    margin: 10px 0;
                }
                .footer {
                    border-top: 1px solid #ecf0f1;
                    padding-top: 15px;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #95a5a6;
                    text-align: center;
                }
                .emoji-hoje { color: #c0392b; font-size: 18px; }
                .emoji-proximo { color: #e67e22; font-size: 18px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Contas a Pagar</h1>
                    <p>Próximos 3 dias de vencimento</p>
                </div>
                <div class="contas">
        """
        
        if not contas:
            html += '<p style="text-align: center; color: #27ae60; font-size: 16px;">✅ Nenhuma conta vencendo nos próximos 3 dias</p>'
        else:
            for conta in contas:
                emoji = '<span class="emoji-hoje">🔴 VENCE HOJE</span>' if conta['dias_faltam'] == 0 else '<span class="emoji-proximo">🟡 AMANHÃ</span>' if conta['dias_faltam'] == 1 else '🟠'
                
                classe = 'hoje' if conta['dias_faltam'] == 0 else 'proximo'
                
                html += f"""
                <div class="conta-item {classe}">
                    {emoji}
                    <p class="fornecedor">{conta['fornecedor']}</p>
                    <p class="valor">R$ {conta['valor']:.2f}</p>
                    <p class="dados"><strong>Vencimento:</strong> {conta['vencimento']}</p>
                    <p class="dados"><strong>Forma de pagamento:</strong> {conta['forma_pagamento']}</p>
                    {f'<p class="dados"><strong>Dados:</strong> {conta["dados_pagamento"]}</p>' if conta['dados_pagamento'] else ''}
                    <p class="dados"><strong>ID:</strong> #{conta['id']}</p>
                </div>
                """
        
        html += """
                </div>
                <div class="footer">
                    <p>Agente de Contas a Pagar • """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</p>
                    <p>Use /proximas no Telegram para mais detalhes</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def gerar_alerta_texto(self, contas):
        """Gera versão em texto do alerta"""
        if not contas:
            return "✅ Nenhuma conta vencendo nos próximos 3 dias."
        
        alerta = "📅 CONTAS VENCENDO NOS PRÓXIMOS 3 DIAS:\n\n"
        
        for conta in contas:
            emoji = "🔴 VENCE HOJE" if conta['dias_faltam'] == 0 else "🟡 AMANHÃ" if conta['dias_faltam'] == 1 else "🟠"
            
            alerta += f"""{emoji}
{conta['vencimento']} - {conta['fornecedor']}
R$ {conta['valor']:.2f}
Forma: {conta['forma_pagamento']}
Dados: {conta['dados_pagamento'] or 'N/A'}
ID: #{conta['id']}
———————————————————————
"""
        
        return alerta
    
    def enviar_email_alerta(self):
        """Envia alerta por email"""
        contas = self.obter_contas_proximos_dias(dias=3)
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📅 Contas a Pagar - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = self.sender
            msg['To'] = self.destinatario
            
            # Versão em texto
            texto = self.gerar_alerta_texto(contas)
            parte_texto = MIMEText(texto, 'plain', 'utf-8')
            
            # Versão em HTML
            html = self.gerar_html_alerta(contas)
            parte_html = MIMEText(html, 'html', 'utf-8')
            
            msg.attach(parte_texto)
            msg.attach(parte_html)
            
            # Envia
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender, self.senha)
            server.sendmail(self.sender, self.destinatario, msg.as_string())
            server.quit()
            
            print(f"✅ Email enviado para {self.destinatario}")
            return True
        
        except Exception as e:
            print(f"❌ Erro ao enviar email: {e}")
            return False
    
    def enviar_telegram_alerta(self, contas):
        """Envia alerta de contas via Telegram Bot API"""
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not token or not chat_id:
            print("⚠️ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados")
            return False

        texto = self.gerar_alerta_texto(contas)
        cabecalho = f"📅 <b>ALERTA DIÁRIO — {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
        mensagem = cabecalho + texto

        try:
            url = f'https://api.telegram.org/bot{token}/sendMessage'
            r = requests.post(url, json={
                'chat_id': chat_id,
                'text': mensagem,
                'parse_mode': 'HTML'
            }, timeout=10)
            if r.ok:
                print("✅ Alerta enviado via Telegram")
                return True
            else:
                print(f"❌ Telegram respondeu: {r.status_code} — {r.text}")
                return False
        except Exception as e:
            print(f"❌ Erro ao enviar Telegram: {e}")
            return False

    def enviar_alertas_diarios(self):
        """Envia alerta por email E Telegram"""
        contas = self.obter_contas_proximos_dias(dias=3)
        self.enviar_email_alerta()
        self.enviar_telegram_alerta(contas)

    def obter_relatorio_mensal(self):
        """Gera relatório completo do mês"""
        contas = self.db.listar_todas_contas()
        
        hoje = datetime.now()
        mes_atual = f"{hoje.month:02d}/{hoje.year}"
        
        contas_mes = {}
        total_mes = 0
        
        for conta in contas:
            try:
                data_vencimento = datetime.strptime(conta.vencimento, '%d/%m/%Y')
                mes_vencimento = f"{data_vencimento.month:02d}/{data_vencimento.year}"
                
                if mes_vencimento == mes_atual:
                    if conta.categoria not in contas_mes:
                        contas_mes[conta.categoria] = {'contas': [], 'total': 0}
                    
                    contas_mes[conta.categoria]['contas'].append(conta)
                    contas_mes[conta.categoria]['total'] += conta.valor
                    total_mes += conta.valor
            except:
                pass
        
        return {
            'periodo': mes_atual,
            'categorias': contas_mes,
            'total': total_mes,
            'data': datetime.now()
        }

if __name__ == '__main__':
    db = BancoDados(db_type='sqlite', db_file='contas.db')
    gerador = GeradorAlertas(db)
    gerador.enviar_email_alerta()
