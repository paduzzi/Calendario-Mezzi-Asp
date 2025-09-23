import streamlit as st
import pandas as pd
import datetime

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

st.write(f"📅 Settimana dal **{inizio_settimana}** al **{fine_settimana}**")

# Giorni della settimana
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [g.strftime("%a %d/%m") for g in giorni]

# --- COSTRUZIONE TABELLA CALENDARIO ---
calendario = pd.DataFrame(index=mezzi["MODELLO"].dropna().unique(), columns=giorni_labels)

for _, row in prenotazioni.iterrows():
    if inizio_settimana <= row["Data"].date() <= fine_settimana:
        giorno_label = row["Data"].strftime("%a %d/%m")
        info = f"{row['Ora Inizio']}–{row['Ora Fine']} ({row['Utente']})"
        if pd.isna(calendario.at[row["Modello"], giorno_label]):
            calendario.at[row["Modello"], giorno_label] = info
        else:
            calendario.at[row["Modello"], giorno_label] += f"\n{info}"

# Mostra tabella
st.subheader("📊 Vista settimanale tipo calendario")
st.dataframe(calendario.fillna(""), use_container_width=True)

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
