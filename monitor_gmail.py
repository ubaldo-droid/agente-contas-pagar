import os
import pickle
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_python_client import discovery
from agente import AgenteContasPagar
from database import BancoDados
import json
from datetime import datetime

class MonitorGmail:
    def __init__(self, database):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        self.service = self.autenticar_gmail()
        self.agente = AgenteContasPagar()
        self.db = database
        self.label_monitorado = os.getenv('GMAIL_LABEL', 'ContasAPagar')
    
    def autenticar_gmail(self):
        """Autentica com Gmail"""
        creds = None
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json'), 
                    self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return discovery.build('gmail', 'v1', credentials=creds)
    
    def obter_emails_nao_lidos(self, max_resultados=5):
        """Busca emails não lidos"""
        try:
            resultados = self.service.users().messages().list(
                userId='me',
                q=f'label:{self.label_monitorado} is:unread',
                maxResults=max_resultados
            ).execute()
            
            return resultados.get('messages', [])
        except Exception as e:
            print(f"❌ Erro ao buscar emails: {e}")
            return []
    
    def obter_corpo_email(self, mensagem_id):
        """Extrai o corpo e anexos do email"""
        try:
            mensagem = self.service.users().messages().get(
                userId='me', 
                id=mensagem_id, 
                format='full'
            ).execute()
            
            headers = mensagem['payload']['headers']
            assunto = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem assunto')
            remetente = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
            
            corpo = ""
            anexos = []
            
            # Extrai corpo
            payload = mensagem['payload']
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            corpo = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    elif 'filename' in part and part['filename']:
                        anexos.append({
                            'nome': part['filename'],
                            'tipo': part['mimeType'],
                            'id': part['body'].get('attachmentId')
                        })
            else:
                if 'data' in payload['body']:
                    corpo = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            return {
                'assunto': assunto,
                'remetente': remetente,
                'corpo': corpo,
                'anexos': anexos,
                'id': mensagem_id
            }
        except Exception as e:
            print(f"❌ Erro ao extrair email: {e}")
            return None
    
    def obter_anexo(self, user_id, message_id, attachment_id, nome_arquivo):
        """Baixa um anexo do email"""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId=user_id,
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            dados = base64.urlsafe_b64decode(attachment['data'])
            return dados
        except Exception as e:
            print(f"❌ Erro ao baixar anexo: {e}")
            return None
    
    def processar_email(self, dados_email):
        """Processa um email com o agente"""
        entrada = f"""
EMAIL PARA ANÁLISE:
Remetente: {dados_email['remetente']}
Assunto: {dados_email['assunto']}
Corpo:
{dados_email['corpo']}
"""
        
        if dados_email['anexos']:
            entrada += f"\nAnexos: {', '.join([a['nome'] for a in dados_email['anexos']])}"
        
        entrada += "\n\nIdentifique se é uma conta a pagar, recebimento ou comprovante de pagamento."
        
        resposta = self.agente.processar_entrada(entrada)
        dados_conta = self.agente.extrair_json_resposta(resposta)
        
        return dados_conta
    
    def salvar_conta_no_banco(self, dados_conta):
        """Salva a conta no banco de dados"""
        if dados_conta and dados_conta.get('tipo_resposta') == 'conta_identificada':
            conta_id = self.db.adicionar_conta(
                vencimento=dados_conta.get('vencimento'),
                fornecedor=dados_conta.get('fornecedor'),
                valor=dados_conta.get('valor'),
                categoria=dados_conta.get('categoria'),
                forma_pagamento=dados_conta.get('forma_pagamento'),
                codigo_pix=dados_conta.get('dados_pagamento'),
                observacoes=dados_conta.get('observacoes', '')
            )
            print(f"✅ Conta #{conta_id} ({dados_conta['fornecedor']}) salva com sucesso!")
            return conta_id
        return None
    
    def salvar_comprovante_no_banco(self, dados_email, dados_comprovante, conta_id):
        """Salva comprovante no banco"""
        if dados_comprovante and dados_comprovante.get('tipo_resposta') == 'comprovante_identificado':
            # Cria pasta se não existir
            pasta = os.getenv('COMPROVANTES_STORAGE_LOCAL', '/app/data/comprovantes')
            os.makedirs(pasta, exist_ok=True)
            
            # Salva arquivo local
            for anexo in dados_email.get('anexos', []):
                arquivo_dados = self.obter_anexo(
                    'me',
                    dados_email['id'],
                    anexo['id'],
                    anexo['nome']
                )
                
                if arquivo_dados:
                    caminho_local = os.path.join(pasta, anexo['nome'])
                    with open(caminho_local, 'wb') as f:
                        f.write(arquivo_dados)
                    
                    self.db.adicionar_comprovante(
                        conta_id=conta_id,
                        arquivo_nome=anexo['nome'],
                        arquivo_tipo=anexo['tipo'],
                        dados_arquivo=arquivo_dados,
                        dados_extraidos=json.dumps(dados_comprovante.get('dados_extraidos', {})),
                        arquivo_local=caminho_local
                    )
    
    def marcar_como_lido(self, mensagem_id):
        """Marca email como lido"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=mensagem_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except Exception as e:
            print(f"❌ Erro ao marcar email como lido: {e}")
    
    def monitorar_continuamente(self):
        """Monitora emails continuamente"""
        print("🔔 Monitorando Gmail...")
        
        emails = self.obter_emails_nao_lidos()
        
        if not emails:
            print("✅ Nenhum email novo")
            return
        
        print(f"📧 Encontrados {len(emails)} emails não lidos")
        
        for email in emails:
            dados_email = self.obter_corpo_email(email['id'])
            
            if dados_email:
                print(f"\n📮 Processando: {dados_email['assunto']}")
                
                # Processa com agente
                dados_conta = self.processar_email(dados_email)
                
                # Salva no banco
                if dados_conta:
                    if dados_conta.get('tipo_resposta') == 'conta_identificada':
                        conta_id = self.salvar_conta_no_banco(dados_conta)
                    elif dados_conta.get('tipo_resposta') == 'comprovante_identificado' and dados_email.get('anexos'):
                        # Procura conta correspondente (simplificado)
                        self.salvar_comprovante_no_banco(dados_email, dados_conta, 1)
                
                # Marca como lido
                self.marcar_como_lido(email['id'])

if __name__ == '__main__':
    db = BancoDados(db_type='sqlite', db_file='contas.db')
    monitor = MonitorGmail(db)
    monitor.monitorar_continuamente()
