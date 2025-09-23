import streamlit as st
import pandas as pd
import datetime
import locale
from io import BytesIO

# Imposta lingua italiana
try:
    locale.setlocale(locale.LC_TIME, "it_IT.utf8")
except:
    pass

# --- CARICA MEZZI ---
@st.cache_data
def load_mezzi():
    df = pd.read_excel("Automezzi ASP (8).xlsx", skiprows=1)
    # Combiniamo modello + targa (se presenti entrambe le colonne)
    if "MODELLO" in df.columns and "TARGA" in df.columns:
        df["MEZZO_COMPLETO"] = df["MODELLO"].astype(str) + " (" + df["TARGA"].astype(str) + ")"
    else:
        df["MEZZO_COMPLETO"] = df["MODELLO"].astype(str)
    return df

mezzi = load_mezzi()

# --- CARICA PRENOTAZIONI ---
try:
    prenotazioni = pd.read_csv("prenotazioni.csv", parse_dates=["Data"])
except FileNotFoundError:
    prenotazioni = pd.DataFrame(columns=["Mezzo", "Data", "Ora Inizio", "Ora Fine", "Utente"])

st.title("🚐 Calendario prenotazioni automezzi")

# --- NAVIGAZIONE SETTIMANA ---
oggi = datetime.date.today()
if "inizio_settimana" not in st.session_state:
    st.session_state.inizio_settimana = oggi - datetime.timedelta(days=oggi.weekday())

inizio_settimana = st.session_state.inizio_settimana
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

st.write(f"📅 Settimana dal **{inizio_settimana.strftime('%-d/%-m/%Y')}** al **{fine_settimana.strftime('%-d/%-m/%Y')}**")

# Giorni della settimana in italiano, formato G/M/A
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [g.strftime("%A %-d/%-m/%Y").capitalize() for g in giorni]

# --- COSTRUZIONE TABELLA CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MEZZO_COMPLETO"].dropna().unique(), columns=giorni_labels)

if not prenotazioni.empty:
    for _, row in prenotazioni.iterrows():
        if inizio_settimana <= row["Data"].date() <= fine_settimana:
            giorno_label = row["Data"].strftime("%A %-d/%-m/%Y").capitalize()
            if row["Mezzo"] not in calendario.index:
                continue
            ora_inizio = pd.to_datetime(str(row["Ora Inizio"])).strftime("%H:%M")
            ora_fine = pd.to_datetime(str(row["Ora Fine"])).strftime("%H:%M")
            info = f"{ora_inizio}–{ora_fine} ({row['Utente']})"
            if pd.isna(calendario.at[row["Mezzo"], giorno_label]):
                calendario.at[row["Mezzo"], giorno_label] = info
            else:
                calendario.at[row["Mezzo"], giorno_label] += f"\n{info}"

# --- STILE E COLORI ---
def color_cells(val):
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    else:
        return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- MOSTRARE CALENDARIO ---
col1, col2, col3 = st.columns([5,1,1])
with col1:
    st.subheader("📊 Calendario settimanale")
with col2:
    if st.button("⬅️", key="prev"):
        st.session_state.inizio_settimana -= datetime.timedelta(days=7)
with col3:
    if st.button("➡️", key="next"):
        st.session_state.inizio_settimana += datetime.timedelta(days=7)

# CSS per colori e testo a capo
st.markdown(
    """
    <style>
    table {
        border-collapse: collapse;
        width: 100%;
    }
    th {
        background-color: #90EE90 !important; /* verde chiaro */
        color: black !important;
        padding: 6px;
        text-align: center;
        border: 1px solid #bbb;
    }
    th:first-child {
        background-color: white !important; /* colonna mezzi */
        color: black !important;
        font-weight: bold;
    }
    td {
        border: 1px solid #bbb;
        padding: 6px;
        vertical-align: top;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 14px;
    }
    td:first-child {
        background-color: white !important;
        color: black !important;
        font-weight: bold;
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
    mezzo = st.selectbox("Seleziona mezzo", mezzi["MEZZO_COMPLETO"].dropna().unique())
    data = st.date_input("Data", oggi)
    ora_inizio = st.time_input("Ora inizio", datetime.time(9, 0))
    ora_fine = st.time_input("Ora fine", datetime.time(17, 0))
    utente = st.text_input("Nome utente")
    submit = st.form_submit_button("Prenota")

if submit:
    nuova = pd.DataFrame([[mezzo, data, ora_inizio, ora_fine, utente]],
                         columns=["Mezzo", "Data", "Ora Inizio", "Ora Fine", "Utente"])
    prenotazioni = pd.concat([prenotazioni, nuova], ignore_index=True)
    prenotazioni.to_csv("prenotazioni.csv", index=False)
    st.success("✅ Prenotazione registrata!")
