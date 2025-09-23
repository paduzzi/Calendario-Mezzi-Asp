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

# Carica mezzi
@st.cache_data
def load_mezzi():
    df = pd.read_excel("Automezzi ASP (8).xlsx", skiprows=1)
    # Combiniamo MODELLO + TARGA
    df["MEZZO_COMPLETO"] = df["MODELLO"].astype(str) + " (" + df["TARGA"].astype(str) + ")"
    return df

mezzi = load_mezzi()

# Carica prenotazioni
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

st.write(f"📅 Settimana dal **{inizio_settimana.strftime('%d/%m/%Y')}** al **{fine_settimana.strftime('%d/%m/%Y')}**")

# Giorni settimana (formato G/M/A)
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [g.strftime("%A %d/%m/%Y").capitalize() for g in giorni]

# --- COSTRUZIONE CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MEZZO_COMPLETO"].dropna().unique(), columns=giorni_labels)

for _, row in prenotazioni.iterrows():
    if inizio_settimana <= row["Data"].date() <= fine_settimana:
        giorno_label = row["Data"].strftime("%A %d/%m/%Y").capitalize()
        ora_inizio = pd.to_datetime(str(row["Ora Inizio"])).strftime("%H:%M")
        ora_fine = pd.to_datetime(str(row["Ora Fine"])).strftime("%H:%M")
        info = f"{ora_inizio}–{ora_fine} ({row['Utente']})"
        if pd.isna(calendario.at[row["Mezzo"], giorno_label]):
            calendario.at[row["Mezzo"], giorno_label] = info
        else:
            calendario.at[row["Mezzo"], giorno_label] += f"\n{info}"

# --- STILE CELLE ---
def color_cells(val):
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    else:
        return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- MOSTRARE CALENDARIO ---
col1, col2 = st.columns([3,1])
with col1:
    st.subheader("📊 Calendario settimanale")
with col2:
    if st.button("⬅️", key="prev"):
        st.session_state.inizio_settimana -= datetime.timedelta(days=7)
    if st.button("➡️", key="next"):
        st.session_state.inizio_settimana += datetime.timedelta(days=7)

# CSS per tabella
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
        padding: 8px;
        text-align: center;
        border: 1px solid #bbb;
    }
    th:first-child {
        background-color: white !important;
        color: black !important;
        font-weight: bold;
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

# --- PULSANTE DOWNLOAD EXCEL ---
if not prenotazioni.empty:
    buffer = BytesIO()
    prenotazioni.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button(
        label="📥 Scarica prenotazioni (Excel)",
        data=buffer,
        file_name="prenotazioni_automezzi.xlsx",
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
