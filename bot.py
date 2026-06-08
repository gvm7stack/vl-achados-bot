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
        "credenciais.json", scopes=escopos
    )
    return gspread.authorize(credenciais)

def enviar_mensagem(texto):
    url   = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dados = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "HTML"}
    resposta = requests.post(url, data=dados)
    return resposta.status_code == 200

# ── ABA AGENDA DE COBRANÇAS ──────────────────────────────
def verificar_agenda():
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

        nome_cliente  = linha[0]   # col A
        produto       = linha[2]   # col C
        valor_parcela = linha[7]   # col H
        restante      = linha[9]   # col J
        status        = linha[11]  # col L

        if "Atrasado" in str(status):
            atrasados.append(
                f"• {nome_cliente} — {produto}\n"
                f"  💰 Parcela: {valor_parcela} | Restante: {restante}"
            )
        elif "Vence em breve" in str(status):
            vencendo.append(
                f"• {nome_cliente} — {produto}\n"
                f"  💰 Parcela: {valor_parcela} | Restante: {restante}"
            )

    return atrasados, vencendo

# ── ABA EMPRÉSTIMOS ──────────────────────────────────────
def verificar_emprestimos():
    cliente  = conectar_sheets()
    planilha = cliente.open("SISTEMA VL")
    aba      = planilha.worksheet("💳 Empréstimos")
    dados    = aba.get_all_values()

    hoje = date.today()
    emp_atrasados = []
    emp_vencendo  = []

    # Tabela começa linha 5 (índice 4), colunas:
    # A=Cliente, B=WA, C=ValorDado, D=ValorReceber, F=QtdParc,
    # G=ValorParc, H=ParcelasRecebidas, J=Saldo, K=Status,
    # N=Data1ºPgto, O=PróxVencimento, P=Situação
    for linha in dados[4:22]:
        if not linha[0]:
            continue

        nome    = linha[0]   # A
        valor_p = linha[6]   # G — valor por parcela
        saldo   = linha[9]   # J — saldo restante
        status  = linha[10]  # K
        situacao= linha[15] if len(linha) > 15 else ""  # P

        if status == "Quitado":
            continue

        if "Atrasado" in str(situacao):
            emp_atrasados.append(
                f"• {nome} — Empréstimo\n"
                f"  💰 Parcela: {valor_p} | Saldo: {saldo}"
            )
        elif "Vence em breve" in str(situacao):
            emp_vencendo.append(
                f"• {nome} — Empréstimo\n"
                f"  💰 Parcela: {valor_p} | Saldo: {saldo}"
            )

    return emp_atrasados, emp_vencendo

# ── GERAR RELATÓRIO COMPLETO ─────────────────────────────
def gerar_relatorio():
    hoje = date.today()

    atrasados, vencendo         = verificar_agenda()
    emp_atrasados, emp_vencendo = verificar_emprestimos()

    msg = f"🔴 <b>VL Achados — Relatório {hoje.strftime('%d/%m/%Y')}</b>\n\n"

    # Cobranças da Agenda
    if atrasados:
        msg += "🚨 <b>PARCELAS ATRASADAS:</b>\n"
        msg += "\n".join(atrasados) + "\n\n"

    if vencendo:
        msg += "⚠️ <b>PARCELAS VENCEM EM BREVE:</b>\n"
        msg += "\n".join(vencendo) + "\n\n"

    # Empréstimos
    if emp_atrasados:
        msg += "🔴 <b>EMPRÉSTIMOS ATRASADOS:</b>\n"
        msg += "\n".join(emp_atrasados) + "\n\n"

    if emp_vencendo:
        msg += "💳 <b>EMPRÉSTIMOS VENCEM EM BREVE:</b>\n"
        msg += "\n".join(emp_vencendo) + "\n\n"

    # Tudo em dia
    if not any([atrasados, vencendo, emp_atrasados, emp_vencendo]):
        msg += "✅ Tudo em dia! Nenhum vencimento próximo."

    enviar_mensagem(msg)
    print("Mensagem enviada com sucesso!")
    print(f"  Cobranças atrasadas: {len(atrasados)}")
    print(f"  Cobranças vencendo: {len(vencendo)}")
    print(f"  Empréstimos atrasados: {len(emp_atrasados)}")
    print(f"  Empréstimos vencendo: {len(emp_vencendo)}")

gerar_relatorio()
