# 🚀 GUIA RÁPIDO DE SETUP

## ⚡ 5 Passos para começar (15 minutos)

### Passo 1: Preparar o ambiente (2 min)

```bash
# Entrar na pasta
cd agente-contas-pagar

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Mac/Linux)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Passo 2: Configurar Claude API (2 min)

1. Acesse: [console.anthropic.com](https://console.anthropic.com/)
2. Clique em **API Keys** → **Create Key**
3. Copie a chave (começa com `sk-ant-`)

### Passo 3: Obter credentials do Gmail (5 min)

1. Acesse: [console.cloud.google.com](https://console.cloud.google.com/)
2. **Criar novo projeto** → nome "Agente Contas"
3. Procurar por **Gmail API** → **Ativar**
4. **Credenciais** → **+ Criar Credencial** → **OAuth 2.0**
5. Tipo: **Aplicativo de Desktop**
6. **Criar**
7. **Download** → salvar como `credentials.json` na pasta do projeto

### Passo 4: Configurar Telegram (3 min)

**Obter Token do Bot:**
1. Abra Telegram
2. Procure: **@BotFather**
3. Envie: `/newbot`
4. Siga as instruções
5. BotFather retorna token (ex: `123456:ABC-DEF...`)

**Obter Chat ID:**
1. Procure: **@userinfobot**
2. Envie qualquer mensagem
3. Retorna seu Chat ID (número)

### Passo 5: Preencher .env (3 min)

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Abrir .env em seu editor e preencher:
```

**Minimal** (essencial):
```
ANTHROPIC_API_KEY=sk-ant-seu-api-key-aqui
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_MONITORED_ADDRESS=ubaldostarlinkmini@gmail.com
GMAIL_LABEL=ContasAPagar
EMAIL_SENDER=ubaldostarlinkmini@gmail.com
EMAIL_SENDER_PASSWORD=sua-senha-de-app-gmail
EMAIL_RECIPIENT=ubaldo@juvenizjr.com.br
TELEGRAM_BOT_TOKEN=seu-token-botfather-aqui
TELEGRAM_CHAT_ID=seu-numero-de-chat-aqui
```

---

## ✅ Criar banco de dados

```bash
python database.py
```

Você deve ver:
```
✅ Tabelas criadas/verificadas com sucesso
✅ Categorias padrão inseridas
```

---

## 🎬 Começar!

```bash
python main.py
```

Você deve ver:
```
============================================================
🤖 AGENTE DE CONTAS A PAGAR
============================================================

⏰ Iniciado em: 21/05/2026 14:30:45

📋 COMPONENTES ATIVOS:
  ✅ Banco de dados (SQLite)
  ✅ Monitor Gmail (a cada 30 min)
  ✅ Telegram Bot (24/7)
  ✅ Alertas diários (08:00)

📞 PRÓXIMOS PASSOS:
  1. Envie um email para seu rótulo 'ContasAPagar'
  2. Use /ajuda no Telegram para comandos
  3. Digite /status para verificar tudo

============================================================
```

---

## 💭 Próximas ações

### No Gmail:
1. Crie um rótulo chamado **"ContasAPagar"**
2. Encaminhe um email de teste (ex: de um fornecedor)
3. Adicione o rótulo
4. Agente vai processar automaticamente em até 30 minutos

### No Telegram:
1. Procure seu bot (usando o username do BotFather)
2. Clique em **START**
3. Envie: `/status`
4. Bot responde com informações

### Teste final:
1. Envie um email com uma conta:
   ```
   Assunto: Nova conta
   Corpo: Eldorado Brasil - R$ 5.000 - vence 20/05 - transferência CC 0000
   ```
2. Adicione rótulo "ContasAPagar"
3. Aguarde 30 segundos a 2 minutos
4. Telegram avisa: "✅ Conta registrada"

---

## 🆘 Problemas comuns?

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "credentials.json not found"
Baixe novamente do Google Cloud Console

### "Telegram token inválido"
Copie exatamente do @BotFather sem espaços

### "Email not sent"
1. Ative 2FA no Gmail
2. Crie senha de app em apppasswords
3. Use a senha de app (não a senha da conta)

---

## 📚 Próximas leituras

- **README.md** - Documentação completa
- **database.py** - Entender o banco
- **.env.example** - Todas as configurações possíveis

---

## 🎯 Checklist final

- [ ] Python 3.11+ instalado
- [ ] Pasta do projeto criada
- [ ] venv ativado
- [ ] requirements.txt instalado
- [ ] `.env` preenchido
- [ ] credentials.json salvo
- [ ] banco criado (python database.py)
- [ ] `python main.py` rodando
- [ ] Telegram /status recebido
- [ ] Email de teste enviado

---

**Pronto!** Seu agente está rodando 24/7 👏
