import streamlit as st
import pandas as pd
import datetime
import locale

# Imposta lingua italiana per i giorni
try:
    locale.setlocale(locale.LC_TIME, "it_IT.utf8")
except:
    pass  # fallback se locale non disponibile

# Carica mezzi
@st.cache_data
def load_mezzi():
    df = pd.read_excel("Automezzi ASP (8).xlsx", skiprows=1)
    return df

mezzi = load_mezzi()

# Carica prenotazioni
try:
    prenotazioni = pd.read_csv("prenotazioni.csv", parse_dates=["Data"])
except FileNotFoundError:
    prenotazioni = pd.DataFrame(columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"])

st.title("🚐 Calendario prenotazioni automezzi")

# --- NAVIGAZIONE SETTIMANA ---
oggi = datetime.date.today()
if "inizio_settimana" not in st.session_state:
    st.session_state.inizio_settimana = oggi - datetime.timedelta(days=oggi.weekday())

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("⬅️ Settimana precedente"):
        st.session_state.inizio_settimana -= datetime.timedelta(days=7)
with col3:
    if st.button("➡️ Settimana successiva"):
        st.session_state.inizio_settimana += datetime.timedelta(days=7)

inizio_settimana = st.session_state.inizio_settimana
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

st.write(f"📅 Settimana dal **{inizio_settimana.strftime('%d %B %Y')}** al **{fine_settimana.strftime('%d %B %Y')}**")

# Giorni della settimana in italiano
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [g.strftime("%A %d/%m").capitalize() for g in giorni]

# --- COSTRUZIONE TABELLA CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MODELLO"].dropna().unique(), columns=giorni_labels)

for _, row in prenotazioni.iterrows():
    if inizio_settimana <= row["Data"].date() <= fine_settimana:
        giorno_label = row["Data"].strftime("%A %d/%m").capitalize()
        ora_inizio = pd.to_datetime(str(row["Ora Inizio"])).strftime("%H:%M")
        ora_fine = pd.to_datetime(str(row["Ora Fine"])).strftime("%H:%M")
        info = f"{ora_inizio}–{ora_fine} ({row['Utente']})"
        if pd.isna(calendario.at[row["Modello"], giorno_label]):
            calendario.at[row["Modello"], giorno_label] = info
        else:
            calendario.at[row["Modello"], giorno_label] += f"\n{info}"

# --- AGGIUNGI COLORI CELLE ---
def color_cells(val):
    """Applica colore giallo chiaro se la cella ha prenotazioni, bianco se vuota"""
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    else:
        return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- MOSTRARE LA TABELLA ---
st.subheader("📊 Vista settimanale tipo calendario")

# CSS aggiuntivo per intestazioni e prima colonna
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
        padding: 8px;
        text-align: center;
        border: 1px solid #bbb;
    }
    th:first-child {
        background-color: white !important; /* colonna Modello */
        color: black !important;
        font-weight: bold;
    }
    td:first-child {
        background-color: white !important; /* celle Modello */
        color: black !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.write(styled_calendario.to_html(), unsafe_allow_html=True)

# --- FORM NUOVA PRENOTAZIONE ---
st.subheader("➕ Nuova prenotazione")
with st.form("nuova_prenotazione"):
    mezzo = st.selectbox("Seleziona mezzo", mezzi["MODELLO"].dropna().unique())
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
