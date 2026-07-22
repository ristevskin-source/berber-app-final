import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# KONFIGURACIJA
RADNO_VREME = [(9, 0), (20, 0)]
INTERVAL_MIN = 15
BROJ_DANA = 7

def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    conn.commit()
    conn.close()

init_db()

st.title("Zakazivanje termina")

# Logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("IMG_20260718_151846.jpg", width=300)

# Admin
with st.expander("🔑 Admin pristup"):
    if "admin" not in st.session_state:
        st.session_state.admin = False
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        if st.button("🔄 Resetuj sve termine"):
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL")
            conn.commit()
            conn.close()
            st.success("Svi termini su slobodni!")
            st.rerun()
        st.subheader("Pregled zakazanih")
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT * FROM rezervacije WHERE ime IS NOT NULL")
        for t in c.fetchall():
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{t[1]}** | {t[2]} {t[3]} - {t[4]} ({t[5]})")
            if col2.button("Oslobodi", key=f"del_{t[0]}"):
                c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL WHERE id=?", (t[0],))
                conn.commit()
                st.rerun()
        conn.close()

# Rezervacija
st.subheader("Rezervacija")
conn = sqlite3.connect('termini.db')
c = conn.cursor()
c.execute("SELECT DISTINCT datum FROM rezervacije")
datumi = [r[0] for r in c.fetchall()]
conn.close()

with st.form("klijent_forma"):
    ime = st.text_input("Ime i prezime *")
    tel = st.text_input("Telefon *")
    usluga = st.selectbox("Usluga", ["Šišanje", "Brijanje", "Stilizovanje"])
    datum = st.selectbox("Datum", datumi)
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT id, vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum,))
    slobodni = c.fetchall()
    conn.close()
    
    if slobodni:
        mapa = {t[1]: t[0] for t in slobodni}
        termin = st.selectbox("Slobodan termin", list(mapa.keys()))
        if st.form_submit_button("Zakaži"):
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=? WHERE id=?", (ime, tel, usluga, mapa[termin]))
            conn.commit()
            conn.close()
            st.success(f"Uspešno ste zakazali: {usluga}, dana {datum} u {termin}.")
    else:
        st.warning("Nema slobodnih termina.")


