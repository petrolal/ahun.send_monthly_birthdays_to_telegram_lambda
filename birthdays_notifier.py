import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


# =========================
# CONFIG VIA ENVIRONMENT
# =========================

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
WORKSHEET_NAME = os.environ["WORKSHEET_NAME"]
NAME_COLUMN = os.environ["NAME_COLUMN"]
DATE_COLUMN = os.environ["DATE_COLUMN"]

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


# =========================
# GOOGLE SHEETS
# =========================


def get_dataframe():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)

    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    client = gspread.authorize(credentials)

    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)

    records = worksheet.get_all_records()
    return pd.DataFrame.from_records(records)


# =========================
# BUSINESS LOGIC
# =========================


def filter_birthdays_current_month(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    df["data_nascimento"] = pd.to_datetime(
        df[DATE_COLUMN], format="%m/%d/%Y", errors="coerce"
    )

    current_month = pd.Timestamp.now().month

    df_filtered = df[df["data_nascimento"].dt.month == current_month].copy()
    df_filtered["dia"] = df_filtered["data_nascimento"].dt.day

    result = df_filtered.sort_values("dia")[
        [NAME_COLUMN, "data_nascimento"]
    ].reset_index(drop=True)

    result["data_nascimento"] = result["data_nascimento"].dt.strftime("%d/%m/%Y")

    return result.rename(columns={NAME_COLUMN: "nome"})


# =========================
# TELEGRAM
# =========================


def format_message(df: pd.DataFrame) -> str:
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    mes_atual = pd.Timestamp.now().month
    nome_mes = meses[mes_atual - 1]

    if df.empty:
        return f"🎉 Nenhum aniversariante em {nome_mes}."

    message = f"🎉 *Aniversariantes de {nome_mes}*\n\n"

    for _, row in df.iterrows():
        message += f"• {row['nome']} - {row['data_nascimento']}\n"

    return message


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}

    response = requests.post(url, data=payload)

    if response.status_code != 200:
        raise Exception(f"Erro Telegram: {response.text}")


# =========================
# LAMBDA HANDLER
# =========================


def lambda_handler(event, context):
    df = get_dataframe()
    aniversariantes = filter_birthdays_current_month(df)
    mensagem = format_message(aniversariantes)
    send_telegram(mensagem)

    return {"statusCode": 200, "body": "Mensagem enviada com sucesso."}
