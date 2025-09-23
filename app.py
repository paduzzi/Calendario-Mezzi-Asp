import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Calendario prenotazioni automezzi", layout="wide")

# --- CARICA MEZZI ---
@st.cache_data
def load_mezzi():
    df = pd.read_excel("Automezzi ASP (8).xlsx", skiprows=1)
    if "MODELLO" in df.columns and "TARGA" in df.columns:
        df["MODELLO_COMPLETO"] = df["MODELLO"].astype(str) + " (" + df["TARGA"].astype(str) + ")"
    else:
        df["MODELLO_COMPLETO"] = df["MODELLO"].astype(str)
    # indice pulito per confronti robusti
    df["MODELLO_COMPLETO_NORM"] = df["MODELLO_COMPLETO"].str.strip().str.upper()
    return df

mezzi = load_mezzi()

# --- CARICA PRENOTAZIONI ---
try:
    prenotazioni = pd.read_csv("prenotazioni.csv")
except FileNotFoundError:
    prenotazioni = pd.DataFrame(columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"])

# normalizza/converti tipi
if not prenotazioni.empty:
    prenotazioni["Data"] = pd.to_datetime(prenotazioni["Data"], errors="coerce")
    prenotazioni["Modello_NORM"] = prenotazioni["Modello"].astype(str).str.strip().str.upper()

st.title("🚐 Calendario prenotazioni automezzi")

# --- NAVIGAZIONE SETTIMANA (sempre settimana IT corrente + spostamento) ---
oggi = datetime.date.today()
inizio_settimana_base = oggi - datetime.timedelta(days=oggi.weekday())
spostamento = st.session_state.get("spostamento", 0)

col_nav1, col_nav2, col_nav3 = st.columns([5, 1, 1])
with col_nav2:
    if st.button("⬅️", key="prev"):
        spostamento -= 7
with col_nav3:
    if st.button("➡️", key="next"):
        spostamento += 7
st.session_state["spostamento"] = spostamento

inizio_settimana = inizio_settimana_base + datetime.timedelta(days=spostamento)
fine_settimana = inizio_settimana + datetime.timedelta(days=6)

st.write(f"📅 Settimana dal **{inizio_settimana.strftime('%d/%m/%Y')}** al **{fine_settimana.strftime('%d/%m/%Y')}**")

# Giorni in italiano (G/M/A)
giorni_settimana_it = {0:"Lunedì",1:"Martedì",2:"Mercoledì",3:"Giovedì",4:"Venerdì",5:"Sabato",6:"Domenica"}
giorni = [inizio_settimana + datetime.timedelta(days=i) for i in range(7)]
giorni_labels = [f"{giorni_settimana_it[g.weekday()]} {g.day}/{g.month}/{g.year}" for g in giorni]

# --- FORM NUOVA PRENOTAZIONE (prima del calendario!) ---
st.subheader("➕ Nuova prenotazione")
with st.form("nuova_prenotazione"):
    mezzo_sel = st.selectbox("Seleziona mezzo", mezzi["MODELLO_COMPLETO"].dropna().unique())
    data_sel = st.date_input("Data", oggi, format="DD/MM/YYYY")
    ora_inizio_sel = st.time_input("Ora inizio", datetime.time(9, 0))
    ora_fine_sel = st.time_input("Ora fine", datetime.time(17, 0))
    utente_sel = st.text_input("Nome utente")
    submit = st.form_submit_button("Prenota")

if submit:
    # salvataggio con formati coerenti
    nuova = pd.DataFrame(
        [[mezzo_sel,
          data_sel.strftime("%Y-%m-%d"),
          ora_inizio_sel.strftime("%H:%M"),
          ora_fine_sel.strftime("%H:%M"),
          utente_sel]],
        columns=["Modello", "Data", "Ora Inizio", "Ora Fine", "Utente"],
    )
    prenotazioni = pd.concat([prenotazioni, nuova], ignore_index=True)
    prenotazioni.to_csv("prenotazioni.csv", index=False)
    st.success("✅ Prenotazione registrata!")

    # aggiorna strutture in memoria per riflettersi subito nel calendario
    prenotazioni["Data"] = pd.to_datetime(prenotazioni["Data"], errors="coerce")
    prenotazioni["Modello_NORM"] = prenotazioni["Modello"].astype(str).str.strip().str.upper()

# --- COSTRUZIONE CALENDARIO ---
st.subheader("📊 Calendario settimanale")

calendario = pd.DataFrame(index=mezzi["MODELLO_COMPLETO"].dropna().unique(),
                          columns=giorni_labels)

if not prenotazioni.empty:
    index_norm = mezzi.set_index("MODELLO_COMPLETO")["MODELLO_COMPLETO_NORM"].to_dict()
    # mappa inversa: NORM -> originale dell'indice tabella
    norm_to_original = {v: k for k, v in index_norm.items()}

    for _, row in prenotazioni.iterrows():
        if pd.isna(row.get("Data")):
            continue
        data_pren = row["Data"].date()
        if not (inizio_settimana <= data_pren <= fine_settimana):
            continue

        giorno_label = f"{giorni_settimana_it[data_pren.weekday()]} {data_pren.day}/{data_pren.month}/{data_pren.year}"
        mezzo_norm = str(row.get("Modello", "")).strip().upper()

        if mezzo_norm not in norm_to_original:
            # mezzo non presente nell'attuale elenco mezzi → ignora per evitare errori
            continue
        mezzo_originale = norm_to_original[mezzo_norm]

        info = f"{row.get('Ora Inizio','')}–{row.get('Ora Fine','')} ({row.get('Utente','')})".strip()
        if pd.isna(calendario.at[mezzo_originale, giorno_label]):
            calendario.at[mezzo_originale, giorno_label] = info
        else:
            calendario.at[mezzo_originale, giorno_label] += f"\n{info}"

# --- STILE & COLORI (giallo chiaro per prenotate, bianco per vuote) ---
def color_cells(val):
    if pd.isna(val) or val == "":
        return "background-color: white; color: black;"
    return "background-color: #FFFACD; color: black; white-space: pre-wrap;"

styled_calendario = calendario.fillna("").style.applymap(color_cells)

# --- CSS responsive e rendering singolo ---
st.markdown(
    """
    <style>
    table { border-collapse: collapse; width: 100%; }
    th {
        background-color: #90EE90 !important; /* verde chiaro per giorni */
        color: black !important; padding: 6px; text-align: center; border: 1px solid #bbb;
    }
    th:first-child {
        background-color: white !important; color: black !important; font-weight: bold; min-width: 220px;
    }
    td {
        border: 1px solid #bbb; padding: 10px; vertical-align: top;
        white-space: pre-wrap; word-wrap: break-word; font-size: 14px;
    }
    td:first-child {
        background-color: white !important; color: black !important; font-weight: bold; min-width: 220px;
    }
    @media (max-width: 600px) {
        table { font-size: 12px; }
        th, td { padding: 4px; }
    }
    .scrollable-table { overflow-x: auto; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="scrollable-table">', unsafe_allow_html=True)
st.write(styled_calendario.to_html(), unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- DOWNLOAD ---
if not prenotazioni.empty:
    # Tutte
    buf_all = BytesIO()
    prenotazioni.to_excel(buf_all, index=False, engine="openpyxl")
    buf_all.seek(0)
    st.download_button("📥 Scarica tutte le prenotazioni (Excel)", buf_all,
                       file_name="prenotazioni_automezzi.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Solo settimana corrente
    mask = (prenotazioni["Data"].notna()) & \
           (prenotazioni["Data"].dt.date >= inizio_settimana) & \
           (prenotazioni["Data"].dt.date <= fine_settimana)
    week_df = prenotazioni.loc[mask]
    if not week_df.empty:
        buf_week = BytesIO()
        week_df.to_excel(buf_week, index=False, engine="openpyxl")
        buf_week.seek(0)
        st.download_button("📥 Scarica prenotazioni di questa settimana (Excel)",
                           buf_week,
                           file_name=f"prenotazioni_settimana_{inizio_settimana.strftime('%d-%m-%Y')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

