import os
from anthropic import Anthropic, AuthenticationError
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

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
   - Guardar observações relevantes

4. Responder SEMPRE em JSON estruturado

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

REGRA CRÍTICA — MÚLTIPLAS CONTAS:
Quando a mensagem contiver MAIS DE UMA conta, responda com este formato:
{
  "tipo_resposta": "multiplas_contas",
  "contas": [
    { "tipo_resposta": "conta_identificada", ... },
    { "tipo_resposta": "conta_identificada", ... }
  ]
}
Nunca retorne apenas uma conta quando houver várias na mesma mensagem.

EXEMPLO — UMA CONTA:
{
  "tipo_resposta": "conta_identificada",
  "fornecedor": "Eldorado Brasil Celulose",
  "valor": 5000.00,
  "vencimento": "20/05/2026",
  "categoria": "Condomínio",
  "forma_pagamento": "Transferência",
  "dados_pagamento": "CC 0000",
  "observacoes": "Fatura de maio"
}

EXEMPLO — MÚLTIPLAS CONTAS:
{
  "tipo_resposta": "multiplas_contas",
  "contas": [
    {
      "tipo_resposta": "conta_identificada",
      "fornecedor": "Vitor Alexandre",
      "valor": 2500.00,
      "vencimento": "05/06/2026",
      "categoria": "Salário Vitor",
      "forma_pagamento": "PIX",
      "dados_pagamento": "",
      "observacoes": "Salário motorista"
    },
    {
      "tipo_resposta": "conta_identificada",
      "fornecedor": "Edna Maria de Queiroz",
      "valor": 1650.00,
      "vencimento": "05/06/2026",
      "categoria": "Salário Edna",
      "forma_pagamento": "Transferência",
      "dados_pagamento": "",
      "observacoes": "Salário"
    }
  ]
}

EXEMPLO — COMPROVANTE:
{
  "tipo_resposta": "comprovante_identificado",
  "dados_extraidos": {
    "valor": 5000.00,
    "data": "20/05/2026",
    "hora": "14:30",
    "tipo_transacao": "Transferência",
    "instituicao": "Bradesco",
    "status": "Concluído",
    "beneficiario": "Eldorado Brasil Celulose"
  },
  "observacoes": "Comprovante de transferência"
}
IMPORTANTE: sempre extraia o campo "beneficiario" do comprovante (nome do destinatário/favorecido).

PARA DÚVIDAS:
- Se a entrada for vaga ou incompleta, peça esclarecimentos em linguagem natural
- NUNCA invente dados — peça confirmação

CONTEXTO DO USUÁRIO:
- Advogado em São Paulo (Ubaldo)
- Gerencia múltiplas despesas pessoais, familiares e profissionais
- Prefere precisão — evite adivinhar dados
"""

    def processar_entrada(self, entrada: str):
        """Processa uma entrada do usuário (email, mensagem, etc)"""
        self.historico.append({
            "role": "user",
            "content": entrada
        })
        
        resposta = self.cliente.messages.create(
            model="claude-sonnet-4-6",
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

    def processar_arquivo(self, dados_binarios: bytes, media_type: str, nome_arquivo: str, legenda: str = ''):
        """Processa imagem ou PDF com visão do Claude para extrair dados de boletos e contas"""
        import base64

        tipos_imagem = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        conteudo = []

        if media_type == 'application/pdf':
            try:
                from pdf2image import convert_from_bytes
                from io import BytesIO
                paginas = convert_from_bytes(dados_binarios, first_page=1, last_page=3, dpi=150)
                if not paginas:
                    raise ValueError("PDF vazio ou ilegível")
                for pagina in paginas:
                    buf = BytesIO()
                    pagina.save(buf, format='JPEG', quality=85)
                    conteudo.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.standard_b64encode(buf.getvalue()).decode()
                        }
                    })
            except ImportError:
                raise ValueError("Dependência pdf2image não disponível. Verifique se poppler-utils está instalado.")
        elif media_type in tipos_imagem:
            conteudo.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(dados_binarios).decode()
                }
            })
        else:
            raise ValueError(f"Formato não suportado: {media_type}. Use PDF, JPEG, PNG ou WebP.")

        texto_prompt = f"Arquivo recebido: {nome_arquivo}"
        if legenda:
            texto_prompt += f"\nObservação do usuário: {legenda}"
        texto_prompt += (
            "\n\nAnalise este documento (boleto, fatura, comprovante ou imagem de conta a pagar). "
            "Extraia todos os dados disponíveis: código de barras, valor, vencimento, beneficiário, "
            "forma de pagamento, e responda com JSON estruturado conforme seu formato padrão."
        )
        conteudo.append({"type": "text", "text": texto_prompt})

        resposta = self.cliente.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=self.sistema_prompt,
            messages=[{"role": "user", "content": conteudo}]
        )

        conteudo_resposta = resposta.content[0].text
        self.historico.append({"role": "assistant", "content": conteudo_resposta})
        return conteudo_resposta

    def extrair_json_resposta(self, resposta: str):
        """Extrai JSON da resposta do agente (suporta objeto único ou multiplas_contas)"""
        # Tenta objeto JSON
        try:
            inicio = resposta.find('{')
            fim = resposta.rfind('}') + 1
            if inicio != -1 and fim > inicio:
                return json.loads(resposta[inicio:fim])
        except json.JSONDecodeError:
            pass
        # Tenta array JSON
        try:
            inicio = resposta.find('[')
            fim = resposta.rfind(']') + 1
            if inicio != -1 and fim > inicio:
                contas = json.loads(resposta[inicio:fim])
                return {"tipo_resposta": "multiplas_contas", "contas": contas}
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
