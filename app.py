
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date, time
import pytz
import math

st.set_page_config(page_title="Prenotazione Automezzi", layout="wide")

# ----------------------- CONFIGURAZIONE -----------------------
# 1) Foglio Google come database (crea un Google Sheet con un tab 'prenotazioni')
#    In Streamlit Cloud inserisci in Secrets:
#    - gcp_service_account = { ... JSON ... }
#    - gsheet_id = "ID_DEL_TUO_SHEET"
#
# 2) CSV dei mezzi (generato da Excel): caricato nel repo come 'vehicles.csv'
VEHICLES_CSV = "vehicles.csv"

ITALY_TZ = pytz.timezone("Europe/Rome")
DAY_NAMES = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]

# ----------------------- FUNZIONI UTILI -----------------------
@st.cache_data(ttl=60)
def load_vehicles():
    df = pd.read_csv(VEHICLES_CSV)
    df["modello"] = df["modello"].astype(str)
    df["tipologia"] = df["tipologia"].astype(str)
    df["centro_costo"] = df["centro_costo"].astype(str)
    return df

@st.cache_resource
def get_gspread_client():
    # Service Account dalle secrets
    creds_info = st.secrets.get("gcp_service_account", None)
    if creds_info is None:
        st.stop()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def open_or_create_worksheet(client, spreadsheet_id, title):
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=20)
        ws.append_row(["timestamp_utc","data","ora_inizio","ora_fine","settimana_lunedì",
                       "modello","tipologia","centro_costo","firmatario","note"])
    return ws

def get_week_bounds(reference_date=None, week_offset=0):
    # Lunedì come inizio settimana
    now = datetime.now(ITALY_TZ).date()
    d = reference_date or now
    # Portiamo d al lunedì della sua settimana
    monday = d - timedelta(days=(d.weekday()))  # 0 = Monday
    monday = monday + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def dt_it_format(d):
    return f"{d.day}/{d.month}/{d.year}"

@st.cache_data(ttl=20)
def fetch_bookings(spreadsheet_id):
    client = get_gspread_client()
    ws = open_or_create_worksheet(client, spreadsheet_id, "prenotazioni")
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame(columns=["timestamp_utc","data","ora_inizio","ora_fine","settimana_lunedì",
                                     "modello","tipologia","centro_costo","firmatario","note"])
    df = pd.DataFrame(rows)
    # Normalizza tipi
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    return df

def add_booking(spreadsheet_id, record):
    client = get_gspread_client()
    ws = open_or_create_worksheet(client, spreadsheet_id, "prenotazioni")
    ws.append_row([
        record["timestamp_utc"],
        record["data"].isoformat(),
        record["ora_inizio"].strftime("%H:%M"),
        record["ora_fine"].strftime("%H:%M"),
        record["settimana_lunedì"].isoformat(),
        record["modello"],
        record["tipologia"],
        record["centro_costo"],
        record["firmatario"],
        record.get("note","")
    ])

def render_calendar(vehicles_df, bookings_df, week_monday):
    # Costruisci le 7 date della settimana
    days = [week_monday + timedelta(days=i) for i in range(7)]
    day_headers = [f"{DAY_NAMES[i]}<br><small>{dt_it_format(days[i])}</small>" for i in range(7)]
    # Precalcola prenotazioni per (modello, day)
    key_to_items = {}
    for _, bk in bookings_df.iterrows():
        key = (str(bk["modello"]), bk["data"])
        key_to_items.setdefault(key, []).append(bk)
    # CSS semplice
    st.markdown("""
    <style>
    table.cal { width: 100%; border-collapse: collapse; table-layout: fixed; }
    table.cal th, table.cal td { border: 1px solid #d0d0d0; padding: 10px; vertical-align: top; }
    table.cal th { background: #f5f5f5; text-align: center; }
    table.cal td { background: #dff2e1; } /* verde pastello chiaro */
    table.cal td.booked { background: #fff3b0; } /* giallo per prenotati */
    .modello { font-weight: 600; white-space: nowrap; }
    .celltext { white-space: pre-wrap; word-wrap: break-word; font-size: 0.95rem; line-height: 1.3; }
    </style>
    """, unsafe_allow_html=True)

    # Costruisci HTML
    html = []
    html.append('<table class="cal">')
    # Header
    html.append("<thead><tr>")
    html.append('<th style="width:22%">Modello</th>')
    for h in day_headers:
        html.append(f"<th>{h}</th>")
    html.append("</tr></thead>")
    # Body
    html.append("<tbody>")
    for _, row in vehicles_df.iterrows():
        modello = str(row["modello"])
        tr = [f'<td class="modello">{modello}</td>']
        for d in days:
            items = key_to_items.get((modello, d), [])
            if items:
                # costruisci testo con più prenotazioni
                lines = []
                for it in sorted(items, key=lambda r: (r.get("ora_inizio",""), r.get("ora_fine",""))):
                    start = it.get("ora_inizio","")
                    end = it.get("ora_fine","")
                    who = it.get("firmatario","")
                    lines.append(f"{start}–{end} • {who}")
                text = "<br>".join(lines)
                td = f'<td class="booked"><div class="celltext">{text}</div></td>'
            else:
                td = '<td><div class="celltext">&nbsp;</div></td>'
            tr.append(td)
        html.append("<tr>" + "".join(tr) + "</tr>")
    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ----------------------- SIDEBAR: Config -----------------------
st.sidebar.header("Impostazioni")
gsheet_id = st.secrets.get("gsheet_id", None)
if not gsheet_id:
    st.sidebar.error("⚠️ Configura `gsheet_id` e `gcp_service_account` in Secrets.")
vehicles_df = load_vehicles()

# ----------------------- NAVIGAZIONE SETTIMANA -----------------------
st.title("📅 Calendario Prenotazioni Automezzi")

# Mantieni l'offset settimana nei query params
query_params = st.experimental_get_query_params()
week_offset = int(query_params.get("w", [0])[0])

col1, col2, col3 = st.columns([1,1,1])
with col1:
    if st.button("« Settimana precedente"):
        week_offset -= 1
        st.experimental_set_query_params(w=week_offset)
        st.rerun()
with col2:
    if st.button("Oggi"):
        week_offset = 0
        st.experimental_set_query_params(w=week_offset)
        st.rerun()
with col3:
    if st.button("Settimana successiva »"):
        week_offset += 1
        st.experimental_set_query_params(w=week_offset)
        st.rerun()

week_monday, week_sunday = get_week_bounds(week_offset=week_offset)
st.subheader(f"Settimana: {dt_it_format(week_monday)} → {dt_it_format(week_sunday)}")

# ----------------------- FORM PRENOTAZIONE -----------------------
with st.form("prenota"):
    st.markdown("### 📝 Prenota un mezzo")
    # Selezioni richieste
    c1, c2, c3 = st.columns(3)
    with c1:
        modello = st.selectbox("Modello", options=vehicles_df["modello"].tolist())
    with c2:
        # tipologia suggerita dal modello scelto
        tipologia_default = vehicles_df.loc[vehicles_df["modello"]==modello, "tipologia"].iloc[0]
        tipologia = st.selectbox("Tipologia", options=sorted(vehicles_df["tipologia"].unique().tolist()), index=sorted(vehicles_df["tipologia"].unique().tolist()).index(tipologia_default) if tipologia_default in sorted(vehicles_df["tipologia"].unique().tolist()) else 0)
    with c3:
        centro_default = vehicles_df.loc[vehicles_df["modello"]==modello, "centro_costo"].iloc[0]
        centro_costo = st.selectbox("Centro di costo", options=sorted(vehicles_df["centro_costo"].unique().tolist()), index=sorted(vehicles_df["centro_costo"].unique().tolist()).index(centro_default) if centro_default in sorted(vehicles_df["centro_costo"].unique().tolist()) else 0)

    c4, c5, c6 = st.columns(3)
    with c4:
        giorno = st.date_input("Giorno", value=week_monday, min_value=date(2000,1,1), max_value=date(2100,12,31))
    with c5:
        ora_inizio = st.time_input("Orario di inizio", value=time(9,0))
    with c6:
        ora_fine = st.time_input("Orario di fine", value=time(12,0))

    firmatario = st.text_input("Firma (nominativo di chi prenota)")
    note = st.text_area("Note (opzionale)", height=80)

    submitted = st.form_submit_button("Conferma prenotazione")

if submitted:
    if not gsheet_id:
        st.error("❌ Impossibile salvare: manca `gsheet_id` in Secrets.")
    elif not firmatario.strip():
        st.error("❌ Inserisci la firma di chi prenota.")
    elif ora_fine <= ora_inizio:
        st.error("❌ L'orario di fine deve essere successivo a quello di inizio.")
    else:
        record = {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "data": giorno,
            "ora_inizio": datetime.combine(giorno, ora_inizio),
            "ora_fine": datetime.combine(giorno, ora_fine),
            "settimana_lunedì": week_monday,
            "modello": modello,
            "tipologia": tipologia,
            "centro_costo": centro_costo,
            "firmatario": firmatario.strip(),
            "note": note.strip()
        }
        try:
            add_booking(gsheet_id, record)
            st.success("✅ Prenotazione salvata! Il calendario è stato aggiornato.")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Errore nel salvataggio: {e}")

# ----------------------- CALENDARIO -----------------------
if gsheet_id:
    bookings_df = fetch_bookings(gsheet_id)
else:
    bookings_df = pd.DataFrame(columns=["timestamp_utc","data","ora_inizio","ora_fine","settimana_lunedì",
                                        "modello","tipologia","centro_costo","firmatario","note"])

# Filtra settimana corrente
mask = (bookings_df["data"] >= week_monday) & (bookings_df["data"] <= week_sunday)
bookings_week = bookings_df.loc[mask].copy()

# Normalizza stringhe orari per il rendering
if not bookings_week.empty:
    # Ensure strings for ora_inizio and ora_fine
    if "ora_inizio" in bookings_week.columns:
        bookings_week["ora_inizio"] = bookings_week["ora_inizio"].astype(str).str[-8:-3]
    if "ora_fine" in bookings_week.columns:
        bookings_week["ora_fine"] = bookings_week["ora_fine"].astype(str).str[-8:-3]

render_calendar(vehicles_df, bookings_week, week_monday)

st.caption("Suggerimento: usa i pulsanti per spostarti tra le settimane. Il calendario è perpetuo e mostra sempre la settimana selezionata.")


