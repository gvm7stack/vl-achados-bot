
# 🔴 VL Achados — Bot de Alertas Automáticos

Bot Python que monitora cobranças e envia alertas automáticos via Telegram.

## 🚀 Funcionalidades
- Lê planilha do Google Sheets em tempo real
- Detecta parcelas atrasadas e vencimentos próximos
- Envia relatório diário automático via Telegram
- Agendado para rodar todo dia às 8h

## 🛠️ Tecnologias
- Python 3.13
- Google Sheets API (gspread)
- Telegram Bot API
- python-dotenv
- Windows Task Scheduler

## ⚙️ Como funciona
1. Bot conecta no Google Sheets via Service Account
2. Lê a aba de cobranças e analisa os status
3. Monta relatório com atrasados e vencimentos
4. Envia mensagem formatada pro Telegram

## 🔒 Segurança
Credenciais protegidas via .env — nunca expostas no repositório.

## Autor
Gustavo Vieira — github.com/gvm7stack
"@ | Out-File -FilePath README.md -Encoding ascii

git add README.md
git commit -m "fix: corrige README duplicado"
git push
