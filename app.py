import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="Calendario prenotazioni automezzi", layout="wide")

# --- CARICA MEZZI ---
@st.cache_data
def load_mezzi():
    df = pd.read_excel("Automezzi ASP (8).xlsx", skiprows=1)
    if "MODELLO" in df.columns and "TARGA" in df.columns:
        df["MODELLO_COMPLETO"] = df["MODELLO"].astype(str) + " (" + df["TARGA"].astype(str) + ")"
    else:
        df["MODELLO_COMPLETO"] = df["MODELLO"].astype(str)
    return df

mezzi = load_mezzi()

# --- CARICA PRENOTAZIONI ---
try:
    prenotazioni = pd.read_csv("prenotazioni.csv")
    prenotazioni["Data"] = pd.to_datetime(prenotazioni["Data"], errors="coerce")
except FileNotFoundError:
    prenotazioni = pd.DataFrame(columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"])

st.title("🚐 Calendario prenotazioni automezzi")

# --- NAVIGAZIONE SETTIMANA ---
oggi = datetime.date.today()
inizio_settimana = oggi - datetime.timedelta(days=oggi.weekday())
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

spostamento = st.session_state.get("spostamento", 0)
col1, col2, col3 = st.columns([5, 1, 1])
with col2:
    if st.button("⬅️", key="prev"):
        spostamento -= 7
with col3:
    if st.button("➡️", key="next"):
        spostamento += 7
st.session_state["spostamento"] = spostamento

inizio_settimana += datetime.timedelta(days=spostamento)
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

st.write(
    f"📅 Settimana dal **{inizio_settimana.strftime('%d/%m/%Y')}** "
    f"al **{fine_settimana.strftime('%d/%m/%Y')}**"
)

# Giorni in italiano
giorni_settimana_it = {
    0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì",
    4: "Venerdì", 5: "Sabato", 6: "Domenica"
}
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [
    f"{giorni_settimana_it[g.weekday()]} {g.day}/{g.month}/{g.year}" for g in giorni
]

# --- COSTRUZIONE CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MODELLO_COMPLETO"].dropna().unique(), columns=giorni_labels)

if not prenotazioni.empty:
    index_norm = [m.strip().upper() for m in calendario.index]

    for _, row in prenotazioni.iterrows():
        if pd.isna(row["Data"]):
            continue
        data_pren = row["Data"].date()
        if inizio_settimana <= data_pren <= fine_settimana:
            giorno_label = (
                f"{giorni_settimana_it[data_pren.weekday()]} "
                f"{data_pren.day}/{data_pren.month}/{data_pren.year}"
            )
            mezzo_norm = str(row["Modello"]).strip().upper()
            if mezzo_norm not in index_norm:
                continue
            mezzo_reale = calendario.index[index_norm.index(mezzo_norm)]
            info = f"{row['Ora Inizio']}–{row['Ora Fine']} ({row['Utente']})"
            if pd.isna(calendario.at[mezzo_reale, giorno_label]):
                calendario.at[mezzo_reale, giorno_label] = info
            else:
                calendario.at[mezzo_reale, giorno_label] += f"\n{info}"

# --- STILE E COLORI ---
def color_cells(val):
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    else:
        return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- MOSTRARE CALENDARIO ---
st.subheader("📊 Calendario settimanale")

st.markdown(
    """
    <style>
    table {
        border-collapse: collapse;
        width: 100%;
    }
    th {
        background-color: #90EE90 !important;
        color: black !important;
        padding: 6px;
        text-align: center;
        border: 1px solid #bbb;
    }
    th:first-child {
        background-color: white !important;
        color: black !important;
        font-weight: bold;
        min-width: 220px;
    }
    td {
        border: 1px solid #bbb;
        padding: 10px;
        vertical-align: top;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 14px;
    }
    td:first-child {
        background-color: white !important;
        color: black !important;
        font-weight: bold;
        min-width: 220px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="scrollable-table">', unsafe_allow_html=True)
st.write(styled_calendario.to_html(), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- FORM NUOVA PRENOTAZIONE ---
st.subheader("➕ Nuova prenotazione")
with st.form("nuova_prenotazione"):
    mezzo = st.selectbox("Seleziona mezzo", mezzi["MODELLO_COMPLETO"].dropna().unique())
    data = st.date_input("Data", oggi, format="DD/MM/YYYY")
    ora_inizio = st.time_input("Ora inizio", datetime.time(9, 0))
    ora_fine = st.time_input("Ora fine", datetime.time(17, 0))
    utente = st.text_input("Nome utente")
    submit = st.form_submit_button("Prenota")

if submit:
    nuova = pd.DataFrame(
        [[mezzo, data.strftime("%Y-%m-%d"), ora_inizio.strftime("%H:%M"), ora_fine.strftime("%H:%M"), utente]],
        columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"],
    )
    prenotazioni = pd.concat([prenotazioni, nuova], ignore_index=True)
    prenotazioni.to_csv("prenotazioni.csv", index=False)
    st.success("✅ Prenotazione registrata!")
    st.rerun()
