import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

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
    prenotazioni = pd.read_csv("prenotazioni.csv", parse_dates=["Data"])
except FileNotFoundError:
    prenotazioni = pd.DataFrame(columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"])

st.title("🚐 Calendario prenotazioni automezzi")

# --- NAVIGAZIONE SETTIMANA ---
oggi = datetime.date.today()

# sempre settimana corrente (no session_state)
inizio_settimana = oggi - datetime.timedelta(days=oggi.weekday())
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

# pulsanti per spostarsi tra settimane
spostamento = st.session_state.get("spostamento", 0)
col1, col2, col3 = st.columns([5,1,1])
with col2:
    if st.button("⬅️", key="prev"):
        spostamento -= 7
with col3:
    if st.button("➡️", key="next"):
        spostamento += 7
st.session_state["spostamento"] = spostamento

# aggiorna settimana corrente con eventuale spostamento
inizio_settimana += datetime.timedelta(days=spostamento)
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

st.write(f"📅 Settimana dal **{inizio_settimana.strftime('%-d/%-m/%Y')}** al **{fine_settimana.strftime('%-d/%-m/%Y')}**")

# Giorni in italiano
giorni_settimana_it = {
    0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì",
    4: "Venerdì", 5: "Sabato", 6: "Domenica"
}
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [f"{giorni_settimana_it[g.weekday()]} {g.day}/{g.month}/{g.year}" for g in giorni]

# --- COSTRUZIONE CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MODELLO_COMPLETO"].dropna().unique(), columns=giorni_labels)

if not prenotazioni.empty:
    for _, row in prenotazioni.iterrows():
        if inizio_settimana <= row["Data"].date() <= fine_settimana:
            giorno_label = f"{giorni_settimana_it[row['Data'].weekday()]} {row['Data'].day}/{row['Data'].month}/{row['Data'].year}"
            if row["Modello"] not in calendario.index:
                continue
            ora_inizio = pd.to_datetime(str(row["Ora Inizio"])).strftime("%H:%M")
            ora_fine = pd.to_datetime(str(row["Ora Fine"])).strftime("%H:%M")
            info = f"{ora_inizio}–{ora_fine} ({row['Utente']})"
            if pd.isna(calendario.at[row["Modello"], giorno_label]):
                calendario.at[row["Modello"], giorno_label] = info
            else:
                calendario.at[row["Modello"], giorno_label] += f"\n{info}"

# --- STILE E COLORI ---
def color_cells(val):
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    else:
        return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- MOSTRARE CALENDARIO ---
st.subheader("📊 Calendario settimanale")

# CSS per celle più grandi e testo a capo
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
        min-width: 220px; /* celle mezzi più larghe */
    }
    td {
        border: 1px solid #bbb;
        padding: 10px; /* più spazio */
        vertical-align: top;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 14px;
    }
    td:first-child {
        background-color: white !important;
        color: black !important;
        font-weight: bold;
        min-width: 220px; /* celle mezzi più larghe */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.write(styled_calendario.to_html(), unsafe_allow_html=True)

# --- PULSANTI DOWNLOAD ---
if not prenotazioni.empty:
    # Tutte le prenotazioni
    buffer_all = BytesIO()
    prenotazioni.to_excel(buffer_all, index=False, engine="openpyxl")
    buffer_all.seek(0)
    st.download_button(
        label="📥 Scarica tutte le prenotazioni (Excel)",
        data=buffer_all,
        file_name="prenotazioni_automezzi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Solo la settimana corrente
    prenotazioni_settimana = prenotazioni[
        (prenotazioni["Data"].dt.date >= inizio_settimana) &
        (prenotazioni["Data"].dt.date <= fine_settimana)
    ]
    if not prenotazioni_settimana.empty:
        buffer_week = BytesIO()
        prenotazioni_settimana.to_excel(buffer_week, index=False, engine="openpyxl")
        buffer_week.seek(0)
        st.download_button(
            label="📥 Scarica prenotazioni di questa settimana (Excel)",
            data=buffer_week,
            file_name=f"prenotazioni_settimana_{inizio_settimana.strftime('%d-%m-%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- FORM NUOVA PRENOTAZIONE ---
st.subheader("➕ Nuova prenotazione")
with st.form("nuova_prenotazione"):
    mezzo = st.selectbox("Seleziona mezzo", mezzi["MODELLO_COMPLETO"].dropna().unique())
    data = st.date_input("Data", oggi)
    ora_inizio = st.time_input("Ora inizio", datetime.time(9, 0))
    ora_fine = st.time_input("Ora fine", datetime.time(17, 0))
    utente = st.text_input("Nome utente")
    submit = st.form_submit_button("Prenota")

if submit:
    nuova = pd.DataFrame([[mezzo, data, ora_inizio, ora_fine, utente]],
                         columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"])
    prenotazioni = pd.concat([prenotazioni, nuova], ignore_index=True)
    prenotazioni.to_csv("prenotazioni.csv", index=False)
    st.success("✅ Prenotazione registrata!")
