import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_client():
    creds_dict = dict(st.secrets["google_service_account"])
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def get_sheet():
    client = get_client()
    sheet_name = st.secrets["google_sheet"]["sheet_name"]
    return client.open(sheet_name)


def read_worksheet(sheet, name):
    ws = sheet.worksheet(name)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def write_worksheet(sheet, name, df):
    ws = sheet.worksheet(name)
    ws.clear()

    if df.empty:
        ws.update([df.columns.tolist()])
        return

    values = [df.columns.tolist()] + df.astype(str).values.tolist()
    ws.update(values)


def cargar_datos_desde_sheets():
    sheet = get_sheet()

    dias_df = read_worksheet(sheet, "dias")
    ejercicios_df = read_worksheet(sheet, "ejercicios")
    historial_df = read_worksheet(sheet, "historial")
    sesiones_df = read_worksheet(sheet, "sesiones")

    datos = {
        "dias": {},
        "ejercicios": {},
        "historial": [],
        "sesiones": []
    }

    for _, row in dias_df.iterrows():
        ultima = str(row.get("ultima_rutina", "")).strip()

        if ultima and ultima.lower() != "nan":
            ultima_rutina = [x.strip() for x in ultima.split(",") if x.strip()]
        else:
            ultima_rutina = []

        datos["dias"][str(row["dia_id"])] = {
            "nombre": str(row["nombre"]),
            "musculos": str(row["musculos"]),
            "ultima_rutina": ultima_rutina
        }

    for _, row in ejercicios_df.iterrows():
        ejercicio_id = str(row.get("ejercicio_id", "")).strip()

        if not ejercicio_id:
            continue

        datos["ejercicios"][ejercicio_id] = {
            "nombre": str(row["nombre"]),
            "dia": str(row["dia"]),
            "musculo": str(row["musculo"]),
            "peso": str(row["peso"]),
            "series": int(row["series"]),
            "reps": int(row["reps"])
        }

    datos["historial"] = historial_df.to_dict("records")
    datos["sesiones"] = sesiones_df.to_dict("records")

    return datos


def guardar_datos_en_sheets(datos):
    sheet = get_sheet()

    dias_rows = []
    for dia_id, d in datos["dias"].items():
        dias_rows.append({
            "dia_id": dia_id,
            "nombre": d["nombre"],
            "musculos": d["musculos"],
            "ultima_rutina": ",".join(d.get("ultima_rutina", []))
        })

    ejercicios_rows = []
    for ejercicio_id, e in datos["ejercicios"].items():
        ejercicios_rows.append({
            "ejercicio_id": ejercicio_id,
            "nombre": e["nombre"],
            "dia": e["dia"],
            "musculo": e["musculo"],
            "peso": e["peso"],
            "series": e["series"],
            "reps": e["reps"]
        })

    historial_rows = datos.get("historial", [])
    sesiones_rows = datos.get("sesiones", [])

    write_worksheet(
        sheet,
        "dias",
        pd.DataFrame(
            dias_rows,
            columns=["dia_id", "nombre", "musculos", "ultima_rutina"]
        )
    )

    write_worksheet(
        sheet,
        "ejercicios",
        pd.DataFrame(
            ejercicios_rows,
            columns=["ejercicio_id", "nombre", "dia", "musculo", "peso", "series", "reps"]
        )
    )

    write_worksheet(
        sheet,
        "historial",
        pd.DataFrame(
            historial_rows,
            columns=["fecha", "ejercicio_id", "ejercicio", "antes", "despues", "nota"]
        )
    )

    write_worksheet(
        sheet,
        "sesiones",
        pd.DataFrame(
            sesiones_rows,
            columns=["fecha", "dia", "dia_id", "inicio", "fin", "duracion_min", "ejercicios", "ejercicio_ids"]
        )
    )