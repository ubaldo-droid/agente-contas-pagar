# 🤖 Agente de Contas a Pagar

Sistema automatizado para gerenciar contas a pagar, com integração Gmail, Telegram e armazenamento de comprovantes.

## 📋 Índice

1. [Requisitos](#requisitos)
2. [Instalação](#instalação)
3. [Configuração](#configuração)
4. [Como usar](#como-usar)
5. [Arquitetura](#arquitetura)
6. [Troubleshooting](#troubleshooting)

---

## ✅ Requisitos

- Python 3.11+
- Conta Gmail (para ler emails)
- Conta Telegram (para receber alertas)
- Chave API do Claude (Anthropic)
- Conexão com internet

## 🚀 Instalação

### Passo 1: Clonar ou extrair o projeto

```bash
cd agente-contas-pagar
```

### Passo 2: Criar ambiente virtual

```bash
python -m venv venv
```

**Ativar:**
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### Passo 3: Instalar dependências

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração

### 1. Copiar arquivo de exemplo

```bash
cp .env.example .env
```

### 2. Configurar Claude API

1. Acesse [console.anthropic.com](https://console.anthropic.com/)
2. Crie uma nova chave API
3. No arquivo `.env`, preencha:

```
ANTHROPIC_API_KEY=sk-ant-seu-api-key-aqui
```

### 3. Configurar Gmail

#### 3a. Obter credenciais

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto (nome: "Agente Contas")
3. Ative **Gmail API**
4. Crie credencial: **OAuth 2.0 - Aplicação de Desktop**
5. Download do arquivo JSON (salve como `credentials.json` na pasta do projeto)

#### 3b. Preencher `.env`

```
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_MONITORED_ADDRESS=ubaldostarlinkmini@gmail.com
GMAIL_LABEL=ContasAPagar
```

**Importante:** No Gmail, crie um rótulo chamado "ContasAPagar" e mova emails de contas para lá.

### 4. Configurar Email (para alertas)

Se usar Gmail com autenticação de app:

1. Ative 2FA na sua conta Google
2. Crie uma "Senha de App" em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. No `.env`:

```
EMAIL_SENDER=ubaldostarlinkmini@gmail.com
EMAIL_SENDER_PASSWORD=sua-senha-de-app-aqui
EMAIL_RECIPIENT=ubaldo@juvenizjr.com.br
```

### 5. Configurar Telegram

#### 5a. Criar bot

1. Abra Telegram
2. Procure por @BotFather
3. Envie `/newbot`
4. Escolha um nome (ex: Contas Pagar Bot)
5. Escolha um username (ex: @contaspagarbot)
6. BotFather te dá um token: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

#### 5b. Obter Chat ID

1. Abra Telegram
2. Procure por @userinfobot
3. Envie qualquer mensagem
4. Bot retorna seu Chat ID (número)

#### 5c. Preencher `.env`

```
TELEGRAM_BOT_TOKEN=seu-token-aqui
TELEGRAM_CHAT_ID=seu-chat-id-aqui
TELEGRAM_USERNAME=contaspagar
```

### 6. Configurar Banco de Dados

Para começar, use SQLite (padrão):

```
DATABASE_TYPE=sqlite
DATABASE_FILE=contas.db
```

### 7. Criar banco de dados

```bash
python database.py
```

Você deve ver:
```
✅ Tabelas criadas/verificadas com sucesso
✅ Categorias padrão inseridas
```

---

## 💡 Como Usar

### Opção A: Rodando tudo junto (Recomendado)

Arquivo principal que roda Gmail, Telegram e alertas:

```bash
python main.py
```

### Opção B: Componentes separados

**Monitorar Gmail:**
```bash
python monitor_gmail.py
```

**Telegram Bot:**
```bash
python telegram_handler.py
```

**Scheduler (alertas):**
```bash
python scheduler.py
```

---

## 📧 Fluxo de Uso

### Receber e registrar uma conta

1. **Email chega** do fornecedor (ex: Eldorado Brasil)
2. **Você encaminha** para `ubaldostarlinkmini@gmail.com` com rótulo "ContasAPagar"
3. **Agente processa** automaticamente (lê, extrai dados)
4. **Telegram avisa:** "✅ Eldorado Brasil - R$ 5.000 - 20/05 registrada"
5. **No banco:** Conta salva com ID #123

### Enviar comprovante de pagamento

1. **Você paga** a conta (boleto, PIX, transferência)
2. **Você tira** screenshot ou salva PDF
3. **Envia para** seu email com:
   - Assunto: "Comprovante: Eldorado Brasil"
   - Anexo: a imagem/PDF
4. **Agente processa:**
   - Lê o comprovante
   - Extrai dados (valor, data, tipo)
   - Liga à conta original
   - Salva no banco
5. **Armazenado:** Imagem guardada com segurança

### Comandos no Telegram

```
/proximas        → Próximas 3 contas vencendo
/todas          → Todas as contas pendentes
/pagas          → Contas já pagas
/relatorio      → Gastos por categoria
/categorias     → Listar categorias
/paga 123       → Marcar conta #123 como paga
/status         → Status do agente
/ajuda          → Ajuda completa
```

---

## 📊 Arquitetura

```
seu-email (Gmail)
    ↓
[MONITOR GMAIL] ← lê automaticamente
    ↓
[AGENTE CLAUDE] ← processa com IA
    ↓
[BANCO DE DADOS] ← armazena
    ↓
├─ TELEGRAM → Você recebe atualizações
├─ EMAIL → Alertas diários
└─ COMPROVANTES → Guardados com segurança
```

### Componentes

| Arquivo | Função |
|---------|--------|
| `agente.py` | Núcleo (Claude AI) |
| `database.py` | Banco de dados |
| `monitor_gmail.py` | Lê emails Gmail |
| `telegram_handler.py` | Bot Telegram |
| `email_alertas.py` | Alertas por email |
| `scheduler.py` | Agendamento automático |
| `main.py` | Orquestra tudo |

---

## 🐛 Troubleshooting

### Gmail não conecta

**Erro:** "Could not open credentials file"

**Solução:**
1. Verifique se `credentials.json` está na pasta raiz
2. Confirme que o arquivo não está corrompido
3. Baixe novamente do Google Cloud Console

### Telegram não envia mensagens

**Erro:** "Bot token inválido"

**Solução:**
1. Copie exatamente o token do @BotFather
2. Certifique-se que o Chat ID está correto
3. Teste com: `/testapi` no @BotFather

### Email não é enviado

**Erro:** "SMTP auth failed"

**Solução:**
1. Verifique se ativou 2FA no Gmail
2. Crie nova "Senha de App" em apppasswords
3. Use a senha de app (não a senha da conta)

### Agente não reconhece contas

**Erro:** JSON vazio ou "não consegui processar"

**Solução:**
1. Verifique se o email tem dados claros (valor, vencimento, fornecedor)
2. Tente com um assunto mais descritivo
3. Confirme que a categoria existe em `.env`

### Banco de dados corrupto

**Erro:** "Database locked" ou "sqlite3.DatabaseError"

**Solução:**
```bash
rm contas.db
python database.py
```

---

## 📝 Exemplos de uso

### Exemplo 1: Registrar boleto via email

```
Assunto: Nova conta - AES Energia
Corpo:
Prezado,

Segue fatura para pagamento:
Vencimento: 25/05/2026
Valor: R$ 850,00
Código de barras: 12345.67890 12345.678901 12345.678901 1 12345678901234

Obrigado
```

**Agente vai:**
1. Extrair: valor (850), vencimento (25/05), código de barras
2. Classificar como: "Utilidades" ou você especifica
3. Salvar no banco
4. Avisar no Telegram: "✅ AES Energia - R$ 850 - 25/05"

### Exemplo 2: Enviar comprovante

```
Assunto: Comprovante pagamento Eldorado
Anexo: transferencia_eldorado.jpg (screenshot)
Corpo: Paguei via transferência no dia 20/05
```

**Agente vai:**
1. Detectar que é comprovante
2. Ler a imagem (extrair: valor, data, tipo de transação)
3. Ligar à conta original
4. Guardar arquivo com segurança
5. Avisar: "✅ Comprovante armazenado"

### Exemplo 3: Pedir relatório

**No Telegram:**
```
/relatorio
```

**Agente responde:**
```
📊 GASTOS POR CATEGORIA:

Salário Edna: R$ 2.000,00 (25%)
Condomínio: R$ 1.500,00 (18%)
Utilidades: R$ 1.200,00 (15%)
Outros: R$ 3.300,00 (42%)

💰 TOTAL: R$ 8.000,00
```

---

## 🔐 Segurança

### Dados sensíveis

- **`.env`** nunca é commitado (está em `.gitignore`)
- **`credentials.json`** está apenas localmente
- **Comprovantes** são criptografados no armazenamento
- **Banco de dados** pode ser feito backup regularmente

### Backup recomendado

```bash
# Semanal
cp contas.db contas_backup_$(date +%Y%m%d).db
```

---

## 📞 Suporte

Se tiver dúvidas ou erros:

1. Verifique o arquivo de log (se existir)
2. Teste componentes individualmente
3. Confirme que todas as variáveis `.env` estão preenchidas
4. Tente rodar em modo debug

---

## 📜 Licença

Este projeto é de uso pessoal/privado.

---

**Criado com ❤️ por Claude**

Última atualização: 2026-05-21
