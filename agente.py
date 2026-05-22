import os
from anthropic import Anthropic
import json
from datetime import datetime

class AgenteContasPagar:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY não configurada no .env")
        
        self.cliente = Anthropic(api_key=api_key)
        self.historico = []
        self.sistema_prompt = """
Você é um assistente especializado em gestão de contas a pagar e recebimentos financeiros.

SUAS RESPONSABILIDADES:
1. Analisar emails, PDFs, imagens ou mensagens de texto sobre contas a pagar/receber
2. Extrair estruturadamente:
   - Data de vencimento (DD/MM/YYYY)
   - Valor (numérico, sem símbolos)
   - Nome do fornecedor/beneficiário
   - Forma de pagamento (Boleto, PIX, Transferência, Cartão, Outro)
   - Código específico (nº conta, chave PIX, código de barras)
   - Categoria (baseado nas categorias do usuário)

3. Para comprovantes recebidos:
   - Extrair dados de imagens (prints de PIX, transferências, boletos)
   - Extrair de PDFs (boletos, recibos, extratos)
   - Validar se comprovante corresponde à conta registrada
   - Guardar observações relevantes

4. Responder SEMPRE em JSON estruturado para contas identificadas

CATEGORIAS DISPONÍVEIS (use exatamente como está):
- Condomínio
- IPTU
- Curso extra João
- Curso extra Gigi
- Cartão crédito visa BB
- Cartão crédito Mastercard BB
- Cartão crédito visa itaú
- Marina
- Marinheiro
- Babá
- Salário Edna
- Salário Vitor
- Gislaini
- Vale transporte Edna
- Condomínio Manso
- Ajuda Vovó
- CMSP
- Celular
- Cesari
- Outro

EXEMPLO DE RESPOSTA PARA UMA CONTA A PAGAR:
{
  "tipo_resposta": "conta_identificada",
  "acao": "criar",
  "fornecedor": "Eldorado Brasil Celulose",
  "valor": 5000.00,
  "vencimento": "20/05/2026",
  "categoria": "Condomínio",
  "forma_pagamento": "Transferência",
  "dados_pagamento": "CC 0000",
  "confianca": 95,
  "observacoes": "Fatura de maio"
}

EXEMPLO DE RESPOSTA PARA COMPROVANTE:
{
  "tipo_resposta": "comprovante_identificado",
  "arquivo_nome": "transferencia_eldorado.jpg",
  "arquivo_tipo": "jpg",
  "dados_extraidos": {
    "valor": 5000.00,
    "data": "20/05/2026",
    "hora": "14:30",
    "tipo_transacao": "Transferência",
    "instituicao": "Bradesco",
    "status": "Concluído"
  },
  "confianca": 98,
  "observacoes": "Comprovante de transferência para Eldorado"
}

PARA RELATÓRIOS:
- Se o usuário pedir "gastos de maio" ou "relatório", responda com JSON de relatório
- Inclua totais por categoria, tendências, alertas

PARA DÚVIDAS:
- Se a entrada for vaga ou incompleta, peça esclarecimentos em linguagem natural
- NUNCA invente dados — pedes confirmação

CONTEXTO DO USUÁRIO:
- Advogado em São Paulo (Ubaldo)
- Especialista em defesa em ações civis
- Gerencia múltiplas despesas (pessoais, familiares, profissionais)
- Prefere precisão — evite adivinhar dados
"""

    def processar_entrada(self, entrada: str):
        """Processa uma entrada do usuário (email, mensagem, etc)"""
        self.historico.append({
            "role": "user",
            "content": entrada
        })
        
        resposta = self.cliente.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=2000,
            system=self.sistema_prompt,
            messages=self.historico
        )
        
        conteudo_resposta = resposta.content[0].text
        self.historico.append({
            "role": "assistant",
            "content": conteudo_resposta
        })
        
        return conteudo_resposta

    def extrair_json_resposta(self, resposta: str):
        """Extrai JSON da resposta do agente"""
        try:
            inicio = resposta.find('{')
            fim = resposta.rfind('}') + 1
            if inicio != -1 and fim > inicio:
                json_str = resposta[inicio:fim]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        return None

    def limpar_historico(self):
        """Limpa o histórico de conversa"""
        self.historico = []

    def processar_email_conte_udo(self, assunto: str, remetente: str, corpo: str, anexos=None):
        """Processa um email completo"""
        entrada = f"""
EMAIL PARA ANÁLISE:
Remetente: {remetente}
Assunto: {assunto}
Corpo do email:
{corpo}
"""
        
        if anexos:
            entrada += f"\nAnexos recebidos: {', '.join(anexos)}"
        
        entrada += "\n\nPor favor, extraia os dados da conta a pagar/receber ou identifique se é comprovante de pagamento."
        
        return self.processar_entrada(entrada)

if __name__ == '__main__':
    agente = AgenteContasPagar()
    
    # Teste rápido
    entrada_teste = """
    Recebi um email da Eldorado Brasil.
    Diz: "Fatura de aluguel - maio/2026. Valor: R$ 5.000,00. 
    Vencimento: 20/05/2026. Favor transferir para CC: 0000"
    """
    
    resposta = agente.processar_entrada(entrada_teste)
    print("Resposta do agente:")
    print(resposta)
    print("\n✅ JSON extraído:")
    print(json.dumps(agente.extrair_json_resposta(resposta), indent=2, ensure_ascii=False))
