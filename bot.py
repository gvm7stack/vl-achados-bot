import os
import requests
import gspread
import time
import sys
from datetime import date
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── CONEXÃO GOOGLE SHEETS ────────────────────────────────
def conectar_sheets():
    escopos = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciais = Credentials.from_service_account_file(
        "credenciais.json", scopes=escopos
    )
    return gspread.authorize(credenciais)

# ── TELEGRAM: ENVIAR MENSAGEM ─────────────────────────────
def enviar_mensagem(texto, chat_id=None):
    url   = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dados = {"chat_id": chat_id or CHAT_ID, "text": texto, "parse_mode": "HTML"}
    requests.post(url, data=dados)

# ── TELEGRAM: BUSCAR MENSAGENS NOVAS ─────────────────────
def buscar_mensagens(offset=None):
    url    = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []

# ── LÊ AGENDA DE COBRANÇAS ───────────────────────────────
def verificar_agenda():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("📅 Agenda Cobranças")
    dados    = aba.get_all_values()

    atrasados = []; vencendo = []; em_dia = []

    for linha in dados[3:]:
        if not linha[0]: continue
        nome   = linha[0]; prod  = linha[2]
        vparc  = linha[7]; rest  = linha[9]; status = linha[11]
        info = f"• {nome} — {prod}\n  💰 Parcela: {vparc} | Restante: {rest}"
        if "Atrasado" in str(status):      atrasados.append(info)
        elif "Vence em breve" in str(status): vencendo.append(info)
        elif "Em dia" in str(status):      em_dia.append(f"• {nome} — {prod}")

    return atrasados, vencendo, em_dia

# ── LÊ EMPRÉSTIMOS ───────────────────────────────────────
def verificar_emprestimos():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("💳 Empréstimos")
    dados    = aba.get_all_values()

    atrasados = []; vencendo = []; em_dia = []; ativos = []

    for linha in dados[4:22]:
        if not linha[0]: continue
        nome     = linha[0]; vparc = linha[6]
        saldo    = linha[9]; status = linha[10]
        situacao = linha[16] if len(linha) > 16 else ""
        if status == "Quitado": continue
        info = f"• {nome}\n  💰 Parcela: {vparc} | Saldo: {saldo}"
        if "Atrasado" in str(situacao):       atrasados.append(info)
        elif "Vence em breve" in str(situacao): vencendo.append(info)
        elif "Em dia" in str(situacao):       em_dia.append(f"• {nome} | Saldo: {saldo}")
        if status == "Ativo":
            ativos.append(f"• {nome} | Dado: {linha[2]} | Receber: {linha[3]} | Saldo: {saldo}")

    return atrasados, vencendo, em_dia, ativos

# ── COMANDOS ─────────────────────────────────────────────
def cmd_start(chat_id):
    enviar_mensagem(
        "🔴 <b>VL Achados — Bot de Gestão</b>\n\n"
        "Comandos disponíveis:\n\n"
        "📋 /relatorio — Relatório completo\n"
        "📅 /agenda — Cobranças da planilha\n"
        "💳 /emprestimo — Status dos empréstimos\n"
        "💰 /resumo — Números gerais\n"
        "❓ /ajuda — Ver todos os comandos", chat_id)

def cmd_relatorio(chat_id):
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
    enviar_mensagem(msg, chat_id)

def cmd_agenda(chat_id):
    atrasados, vencendo, em_dia = verificar_agenda()
    msg = "📅 <b>AGENDA DE COBRANÇAS</b>\n\n"
    if atrasados:
        msg += f"🚨 <b>Atrasados ({len(atrasados)}):</b>\n" + "\n".join(atrasados) + "\n\n"
    if vencendo:
        msg += f"⚠️ <b>Vence em breve ({len(vencendo)}):</b>\n" + "\n".join(vencendo) + "\n\n"
    if em_dia:
        msg += f"✅ <b>Em dia ({len(em_dia)}):</b>\n" + "\n".join(em_dia) + "\n\n"
    if not any([atrasados, vencendo, em_dia]):
        msg += "✅ Nenhuma cobrança ativa."
    enviar_mensagem(msg, chat_id)

def cmd_emprestimo(chat_id):
    atrasados, vencendo, em_dia, _ = verificar_emprestimos()
    msg = "💳 <b>EMPRÉSTIMOS</b>\n\n"
    if atrasados:
        msg += f"🔴 <b>Atrasados ({len(atrasados)}):</b>\n" + "\n".join(atrasados) + "\n\n"
    if vencendo:
        msg += f"🟡 <b>Vence em breve ({len(vencendo)}):</b>\n" + "\n".join(vencendo) + "\n\n"
    if em_dia:
        msg += f"🟢 <b>Em dia ({len(em_dia)}):</b>\n" + "\n".join(em_dia) + "\n\n"
    if not any([atrasados, vencendo, em_dia]):
        msg += "✅ Nenhum empréstimo ativo."
    enviar_mensagem(msg, chat_id)

def cmd_resumo(chat_id):
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
    enviar_mensagem(msg, chat_id)

def cmd_ajuda(chat_id):
    enviar_mensagem(
        "❓ <b>COMANDOS DISPONÍVEIS</b>\n\n"
        "/start — Boas vindas\n"
        "/relatorio — Relatório completo\n"
        "/agenda — Cobranças da planilha\n"
        "/emprestimo — Status dos empréstimos\n"
        "/resumo — Números gerais\n"
        "/ajuda — Esta mensagem", chat_id)

# ── PROCESSAR COMANDO ─────────────────────────────────────
def processar_comando(texto, chat_id):
    t = texto.strip().lower()
    if t in ["/start","start","oi","olá","ola"]:       cmd_start(chat_id)
    elif t in ["/relatorio","/relatório","relatorio"]: cmd_relatorio(chat_id)
    elif t in ["/agenda","agenda"]:                    cmd_agenda(chat_id)
    elif t in ["/emprestimo","/empréstimo","emprestimo"]: cmd_emprestimo(chat_id)
    elif t in ["/resumo","resumo"]:                    cmd_resumo(chat_id)
    elif t in ["/ajuda","/help","ajuda","help"]:       cmd_ajuda(chat_id)
    else: enviar_mensagem("❓ Comando não reconhecido.\nDigite /ajuda para ver os comandos.", chat_id)

# ── MODO ESCUTAR (python bot.py escutar) ─────────────────
def modo_escutar(duracao=300):
    print(f"🔴 Bot escutando por {duracao}s... (Ctrl+C para parar)")
    offset = None
    inicio = time.time()
    while time.time() - inicio < duracao:
        updates = buscar_mensagens(offset)
        for upd in updates:
            offset = upd["update_id"] + 1
            msg    = upd.get("message", {})
            texto  = msg.get("text", "")
            chat   = msg.get("chat", {}).get("id")
            if texto and chat:
                print(f"  → '{texto}' de {chat}")
                processar_comando(texto, chat)
        time.sleep(2)
    print("Bot encerrado.")

# ── MODO RELATÓRIO DIÁRIO (GitHub Actions) ───────────────
def modo_relatorio_diario():
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
        msg += "✅ Tudo em dia! Nenhum vencimento próximo."
    enviar_mensagem(msg)
    print("Relatório diário enviado!")

# ── EXECUÇÃO ─────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "escutar":
        modo_escutar(duracao=300)
    else:
        modo_relatorio_diario()
