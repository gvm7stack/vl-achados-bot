import os
import requests
import gspread
from flask import Flask, request
from datetime import date, datetime
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# ── GOOGLE SHEETS ─────────────────────────────────────────
def conectar_sheets():
    import json
    escopos = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write(creds_json)
        tmp.close()
        credenciais = Credentials.from_service_account_file(tmp.name, scopes=escopos)
    else:
        credenciais = Credentials.from_service_account_file("credenciais.json", scopes=escopos)
    return gspread.authorize(credenciais)

# ── TELEGRAM ──────────────────────────────────────────────
def enviar(texto, chat_id):
    url   = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dados = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
    requests.post(url, data=dados)

def set_webhook(url):
    endpoint = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    r = requests.post(endpoint, data={"url": url})
    return r.json()

# ── LÊ AGENDA ─────────────────────────────────────────────
def verificar_agenda():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("📅 Agenda Cobranças")
    dados    = aba.get_all_values()

    atrasados = []; vencendo = []; em_dia = []
    for linha in dados[3:]:
        if not linha[0]: continue
        nome      = linha[0]
        prod      = linha[2]
        vparc     = linha[7]
        rest      = linha[9]
        venc_data = linha[9] if len(linha) > 9 else "—"
        status    = linha[11]
        info = f"• {nome} — {prod}\n  💰 Parcela: {vparc} | Restante: {rest} | 📅 {venc_data}"
        if "Atrasado" in str(status):         atrasados.append(info)
        elif "Vence em breve" in str(status): vencendo.append(info)
        elif "Em dia" in str(status):         em_dia.append(f"• {nome} — {prod}")
    return atrasados, vencendo, em_dia

# ── LÊ EMPRÉSTIMOS ────────────────────────────────────────
def verificar_emprestimos():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("💳 Empréstimos")
    dados    = aba.get_all_values()

    atrasados = []; vencendo = []; em_dia = []; ativos = []
    for linha in dados[4:22]:
        if not linha[0]: continue
        nome     = linha[0]
        vparc    = linha[6]
        venc     = linha[8] if len(linha) > 8 else "—"
        saldo    = linha[9]
        status   = linha[10]
        situacao = linha[16] if len(linha) > 16 else ""
        if status == "Quitado": continue
        info = f"• {nome}\n  💰 Parcela: {vparc} | Saldo: {saldo} | 📅 {venc}"
        if "Atrasado" in str(situacao):         atrasados.append(info)
        elif "Vence em breve" in str(situacao): vencendo.append(info)
        elif "Em dia" in str(situacao):         em_dia.append(f"• {nome} | Saldo: {saldo} | 📅 {venc}")
        if status == "Ativo":
            ativos.append(f"• {nome} | Dado: {linha[2]} | Receber: {linha[3]} | Saldo: {saldo}")
    return atrasados, vencendo, em_dia, ativos

# ── LÊ VENCIMENTOS DE HOJE ────────────────────────────────
def verificar_hoje():
    hoje     = date.today()
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")

    # Agenda
    aba   = planilha.worksheet("📅 Agenda Cobranças")
    dados = aba.get_all_values()
    agenda_hoje = []
    for linha in dados[3:]:
        if not linha[0]: continue
        try:
            venc = datetime.strptime(linha[9], "%d/%m/%Y").date()
            if venc == hoje:
                agenda_hoje.append(f"• {linha[0]} — {linha[2]}\n  💰 Parcela: {linha[7]}")
        except:
            continue

    # Empréstimos
    aba   = planilha.worksheet("💳 Empréstimos")
    dados = aba.get_all_values()
    emp_hoje = []
    for linha in dados[4:22]:
        if not linha[0]: continue
        try:
            venc = datetime.strptime(linha[8], "%d/%m/%Y").date()
            if venc == hoje:
                emp_hoje.append(f"• {linha[0]}\n  💰 Parcela: {linha[6]} | Saldo: {linha[9]}")
        except:
            continue

    return agenda_hoje, emp_hoje

# ── COMANDOS ──────────────────────────────────────────────
def cmd_start(chat_id):
    enviar(
        "🔴 <b>VL Achados — Bot de Gestão</b>\n\n"
        "Comandos disponíveis:\n\n"
        "📋 /relatorio — Relatório completo\n"
        "📅 /agenda — Cobranças da planilha\n"
        "💳 /emprestimo — Status dos empréstimos\n"
        "💰 /resumo — Números gerais\n"
        "🗓 /hoje — Vencimentos de hoje\n"
        "❓ /ajuda — Ver todos os comandos", chat_id)

def cmd_relatorio(chat_id):
    enviar("⏳ Gerando relatório...", chat_id)
    hoje = date.today()
    atras_a, venc_a, _ = verificar_agenda()
    atras_e, venc_e, _, _ = verificar_emprestimos()
    msg = f"🔴 <b>VL Achados — Relatório {hoje.strftime('%d/%m/%Y')}</b>\n\n"
    if atras_a:
        msg += "🚨 <b>PARCELAS ATRASADAS:</b>\n" + "\n".join(atras_a) + "\n\n"
    if venc_a:
        msg += "⚠️ <b>VENCE EM BREVE:</b>\n" + "\n".join(venc_a) + "\n\n"
    if atras_e:
        msg += "🔴 <b>EMPRÉSTIMOS ATRASADOS:</b>\n" + "\n".join(atras_e) + "\n\n"
    if venc_e:
        msg += "💳 <b>EMPRÉSTIMOS VENCEM EM BREVE:</b>\n" + "\n".join(venc_e) + "\n\n"
    if not any([atras_a, venc_a, atras_e, venc_e]):
        msg += "✅ Tudo em dia!"
    enviar(msg, chat_id)

def cmd_agenda(chat_id):
    enviar("⏳ Buscando cobranças...", chat_id)
    atrasados, vencendo, em_dia = verificar_agenda()
    msg = "📅 <b>AGENDA DE COBRANÇAS</b>\n\n"
    if atrasados:
        msg += f"🚨 <b>Atrasados ({len(atrasados)}):</b>\n" + "\n".join(atrasados) + "\n\n"
    if vencendo:
        msg += f"⚠️ <b>Vence em breve ({len(vencendo)}):</b>\n" + "\n".join(vencendo) + "\n\n"
    if em_dia:
        msg += f"✅ <b>Em dia ({len(em_dia)}):</b>\n" + "\n".join(em_dia)
    if not any([atrasados, vencendo, em_dia]):
        msg += "✅ Nenhuma cobrança ativa."
    enviar(msg, chat_id)

def cmd_emprestimo(chat_id):
    enviar("⏳ Buscando empréstimos...", chat_id)
    atrasados, vencendo, em_dia, _ = verificar_emprestimos()
    msg = "💳 <b>EMPRÉSTIMOS</b>\n\n"
    if atrasados:
        msg += f"🔴 <b>Atrasados ({len(atrasados)}):</b>\n" + "\n".join(atrasados) + "\n\n"
    if vencendo:
        msg += f"🟡 <b>Vence em breve ({len(vencendo)}):</b>\n" + "\n".join(vencendo) + "\n\n"
    if em_dia:
        msg += f"🟢 <b>Em dia ({len(em_dia)}):</b>\n" + "\n".join(em_dia)
    if not any([atrasados, vencendo, em_dia]):
        msg += "✅ Nenhum empréstimo ativo."
    enviar(msg, chat_id)

def cmd_resumo(chat_id):
    enviar("⏳ Calculando resumo...", chat_id)
    atras_a, venc_a, emdia_a = verificar_agenda()
    atras_e, venc_e, emdia_e, ativos = verificar_emprestimos()
    msg = (
        f"💰 <b>RESUMO VL ACHADOS</b>\n\n"
        f"📅 <b>Agenda:</b>\n"
        f"  🚨 Atrasados: {len(atras_a)}\n"
        f"  ⚠️ Vence em breve: {len(venc_a)}\n"
        f"  ✅ Em dia: {len(emdia_a)}\n\n"
        f"💳 <b>Empréstimos:</b>\n"
        f"  🔴 Atrasados: {len(atras_e)}\n"
        f"  🟡 Vence em breve: {len(venc_e)}\n"
        f"  🟢 Em dia: {len(emdia_e)}\n"
        f"  📊 Total ativo: {len(ativos)}"
    )
    enviar(msg, chat_id)

def cmd_hoje(chat_id):
    enviar("⏳ Verificando vencimentos de hoje...", chat_id)
    agenda_hoje, emp_hoje = verificar_hoje()
    hoje_str = date.today().strftime("%d/%m/%Y")
    msg = f"🗓 <b>VENCIMENTOS HOJE — {hoje_str}</b>\n\n"
    if agenda_hoje:
        msg += f"📋 <b>Cobranças ({len(agenda_hoje)}):</b>\n" + "\n".join(agenda_hoje) + "\n\n"
    if emp_hoje:
        msg += f"💳 <b>Empréstimos ({len(emp_hoje)}):</b>\n" + "\n".join(emp_hoje) + "\n\n"
    if not agenda_hoje and not emp_hoje:
        msg += "✅ Nenhum vencimento hoje."
    enviar(msg, chat_id)

def cmd_ajuda(chat_id):
    enviar(
        "❓ <b>COMANDOS DISPONÍVEIS</b>\n\n"
        "/start — Boas vindas\n"
        "/relatorio — Relatório completo\n"
        "/agenda — Cobranças da planilha\n"
        "/emprestimo — Status dos empréstimos\n"
        "/resumo — Números gerais\n"
        "/hoje — Vencimentos de hoje\n"
        "/ajuda — Esta mensagem", chat_id)

def processar(texto, chat_id):
    t = texto.strip().lower()
    if t in ["/start","start","oi","olá","ola"]:          cmd_start(chat_id)
    elif t in ["/relatorio","/relatório","relatorio"]:    cmd_relatorio(chat_id)
    elif t in ["/agenda","agenda"]:                       cmd_agenda(chat_id)
    elif t in ["/emprestimo","/empréstimo","emprestimo"]: cmd_emprestimo(chat_id)
    elif t in ["/resumo","resumo"]:                       cmd_resumo(chat_id)
    elif t in ["/hoje","hoje"]:                           cmd_hoje(chat_id)
    elif t in ["/ajuda","/help","ajuda"]:                 cmd_ajuda(chat_id)
    else: enviar("❓ Comando não reconhecido. Digite /ajuda", chat_id)

# ── WEBHOOK ENDPOINT ──────────────────────────────────────
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data    = request.get_json()
    message = data.get("message", {})
    texto   = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    if texto and chat_id:
        processar(texto, chat_id)
    return "OK", 200

@app.route("/")
def home():
    return "🔴 VL Achados Bot — Online!", 200

# ── INICIA SERVIDOR ───────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)