import os
import requests
import gspread
from datetime import date
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def conectar_sheets():
    escopos = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credenciais = Credentials.from_service_account_file(
        "credenciais.json",
        scopes=escopos
    )
    return gspread.authorize(credenciais)

def enviar_mensagem(texto):
    url   = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dados = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"}
    resposta = requests.post(url, data=dados)
    return resposta.status_code == 200

def verificar_vencimentos():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("📅 Agenda Cobranças")
    dados    = aba.get_all_values()

    hoje      = date.today()
    atrasados = []
    vencendo  = []

    for linha in dados[3:]:
        if not linha[0]:
            continue

        cliente_nome  = linha[0]
        produto       = linha[2]
        valor_parcela = linha[7]
        restante      = linha[9]
        status        = linha[11]

        if "Atrasado" in str(status):
            atrasados.append(
                f"• {cliente_nome} — {produto}\n"
                f"  💰 Parcela: {valor_parcela} | Restante: {restante}"
            )
        elif "Vence em breve" in str(status):
            vencendo.append(
                f"• {cliente_nome} — {produto}\n"
                f"  💰 Parcela: {valor_parcela} | Restante: {restante}"
            )

    return hoje, atrasados, vencendo

def verificar_emprestimos():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("💳 Empréstimos")
    dados    = aba.get_all_values()

    emprestimos_ativos = []

    # Lê a tabela de empréstimos (linhas 5 a 17, índice 4 a 16)
    for linha in dados[4:17]:
        if not linha[0]:
            continue

        cliente_nome  = linha[0]   # col A
        valor_dado    = linha[2]   # col C — valor emprestado
        valor_receber = linha[3]   # col D — valor a receber
        saldo         = linha[9]   # col J — saldo restante
        status        = linha[10]  # col K — status

        if "Ativo" in str(status) and saldo:
            emprestimos_ativos.append(
                f"• {cliente_nome}\n"
                f"  💸 Emprestado: {valor_dado} | "
                f"💰 A receber: {valor_receber} | "
                f"📊 Saldo: {saldo}"
            )

    return emprestimos_ativos

def gerar_relatorio():
    hoje, atrasados, vencendo = verificar_vencimentos()
    emprestimos = verificar_emprestimos()

    msg = f"🔴 <b>VL Achados — Relatório do dia {hoje.strftime('%d/%m/%Y')}</b>\n\n"

    if atrasados:
        msg += "🚨 <b>ATRASADOS:</b>\n"
        msg += "\n".join(atrasados) + "\n\n"

    if vencendo:
        msg += "⚠️ <b>VENCE EM BREVE:</b>\n"
        msg += "\n".join(vencendo) + "\n\n"

    if emprestimos:
        msg += "💳 <b>EMPRÉSTIMOS ATIVOS:</b>\n"
        msg += "\n".join(emprestimos) + "\n\n"

    if not atrasados and not vencendo and not emprestimos:
        msg += "✅ Tudo em dia! Nenhum vencimento próximo."

    enviar_mensagem(msg)
    print("Mensagem enviada com sucesso!")

gerar_relatorio()