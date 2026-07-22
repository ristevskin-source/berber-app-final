import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta

# ---------- STIL (tamna tema, bledja nijansa) ----------
st.markdown("""
<style>
    .stApp {
        background-color: #2d2d2d;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #d4af37 !important;
    }
    .stButton button {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #e6c86a !important;
        transform: scale(1.02);
    }
    .stMetric {
        background-color: #3a3a3a;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid #d4af37;
        color: #e0e0e0;
    }
    .stMetric label, .stMetric div {
        color: #e0e0e0 !important;
    }
    .stSelectbox, .stTextInput, .stNumberInput {
        background-color: #3a3a3a !important;
        color: #e0e0e0 !important;
    }
    label {
        color: #d0d0d0 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #3a3a3a;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #e0e0e0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold;
    }
    /* Tabela za usluge - zlatne linije */
    .usluge-tabela {
        border-collapse: collapse;
        width: 100%;
        margin: 10px 0;
    }
    .usluge-tabela td, .usluge-tabela th {
        border: 1px solid #d4af37;
        padding: 8px 12px;
        text-align: left;
    }
    .usluge-tabela tr:nth-child(even) {
        background-color: #3a3a3a;
    }
    .usluge-tabela tr:nth-child(odd) {
        background-color: #2d2d2d;
    }
    /* Klijent kartice */
    .klijent-kartica {
        background-color: #3a3a3a;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        border: 2px solid #d4af37;
        box-shadow: 0 2px 8px rgba(212, 175, 55, 0.15);
        transition: 0.2s;
    }
    .klijent-kartica:hover {
        box-shadow: 0 4px 16px rgba(212, 175, 55, 0.3);
        transform: scale(1.002);
    }
</style>
""", unsafe_allow_html=True)

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 15
BROJ_DANA = 7
PAUZA_POCETAK = 12
PAUZA_KRAJ = 13

# ---------- INICIJALIZACIJA BAZE ----------
def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER, naplaceno INTEGER DEFAULT 0, datum_naplate TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (
                    usluga TEXT PRIMARY KEY, 
                    cena INTEGER,
                    trajanje INTEGER
                )''')
    
    usluge = [
        ('💇 Šišanje', 1500, 45),
        ('💇 Šišanje + pranje kose', 1900, 60),
        ('💇 Šišanje + brada', 2000, 60),
        ('💇 Šišanje + brada + pranje kose', 2400, 75),
        ('💇 Šišanje + brada + pranje kose + obrve', 2800, 90),
        ('🧔 Brada (samo)', 1000, 30),
        ('✨ Obrve (samo)', 400, 15)
    ]
    c.executemany("INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)", usluge)
    
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    # Pauze više nisu u admin panelu, ali tabela ostaje (za automatske pauze)
    c.execute('''CREATE TABLE IF NOT EXISTS pauze 
                 (id INTEGER PRIMARY KEY, datum TEXT, vreme TEXT, napomena TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- POMOĆNE FUNKCIJE ----------
def formatiraj_datum(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
    return f"{dani_u_nedelji[dan.weekday()]}, {dan.strftime('%d.%m.%Y')}"

def generisi_datume():
    now = datetime.now()
    if now.hour >= 20:
        start = now + timedelta(days=1)
    else:
        start = now
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    datumi = []
    for i in range(BROJ_DANA):
        dan = start + timedelta(days=i)
        datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_slotove_za_dan(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    
    # ⛔ NEDELJA - NERADNA
    if dan.weekday() == 6:
        return
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    # 🔥 DODAJ AUTOMATSKU PAUZU ZA SVAKI DAN (12-13h)
    # Proveri da li pauza već postoji za ovaj dan
    c.execute("SELECT vreme FROM pauze WHERE datum=? AND vreme BETWEEN '12:00' AND '13:00'", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    
    # Ako nema pauze, dodaj je
    if not pauze:
        # Dodaj pauzu od 12:00 do 13:00 (na svakih 15 min)
        for i in range(PAUZA_POCETAK*4, PAUZA_KRAJ*4):  # 12:00 = 48, 13:00 = 52 (na 15 min)
            vreme = f"{i//4:02d}:{(i%4)*15:02d}"
            c.execute("INSERT INTO pauze (datum, vreme, napomena) VALUES (?, ?, ?)", (datum_str, vreme, "Ručak"))
    
    # Dohvati sve pauze za ovaj dan
    c.execute("SELECT vreme FROM pauze WHERE datum=?", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    
    c.execute("DELETE FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    slotovi = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        if vreme not in pauze:
            slotovi.append((None, datum_str, vreme, None, None, None, 0, None))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    
    if slotovi:
        c.executemany("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, naplaceno, datum_naplate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", slotovi)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_slotove_za_dan(d)

osvezi_termine()

def dovoljno_slobodnih_slotova(datum, pocetak, trajanje):
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC
    """, (datum, pocetak))
    slobodni = [row[0] for row in c.fetchall()]
    conn.close()
    
    if len(slobodni) < broj_slotova:
        return False
    
    for i in range(broj_slotova - 1):
        t1 = datetime.strptime(slobodni[i], "%H:%M")
        t2 = datetime.strptime(slobodni[i+1], "%H:%M")
        if (t2 - t1).seconds // 60 != INTERVAL_MIN:
            return False
    return True

def rezervisi_blok(datum, pocetak, trajanje, ime, telefon, usluga, cena):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    c.execute("""
        SELECT id FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC LIMIT ?
    """, (datum, pocetak, broj_slotova))
    
    ids = [row[0] for row in c.fetchall()]
    
    if len(ids) < broj_slotova:
        conn.close()
        return False
    
    for id in ids:
        c.execute("DELETE FROM rezervacije WHERE id=?", (id,))
    
    for i in range(broj_slotova):
        vreme = (datetime.strptime(pocetak, "%H:%M") + timedelta(minutes=i*INTERVAL_MIN)).strftime("%H:%M")
        c.execute("""
            INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, naplaceno, datum_naplate)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (usluga, datum, vreme, ime, telefon, cena, None))
    
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE ime=? AND datum=? AND vreme=?", (ime, datum, pocetak))
    count = c.fetchone()[0]
    conn.close()
    
    return count > 0

# ---------- UI ----------
st.set_page_config(page_title="💈 Zakazivanje", layout="centered")

try:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("IMG-7dca0f9a0a28a9b8098a0cf36f04adb2-V.jpg", use_column_width=True)
except:
    st.info("🖼️ Logo nije učitan, ali aplikacija radi.")

st.title("💈 Berberski salon - Zakazivanje")

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

# ===================================================================
# TAB 1: KLIJENTI
# ===================================================================
with tab1:
    if 'booking_success' not in st.session_state:
        st.session_state['booking_success'] = False

    if st.session_state['booking_success']:
        detalji = st.session_state['booking_details']
        st.balloons()
        st.markdown(f"""
        <div style="background-color: #3a3a3a; padding: 20px; border-radius: 15px; border-left: 6px solid #d4af37; box-shadow: 0 4px 12px rgba(0,0,0,0.5); margin: 20px 0;">
            <h2 style="color: #d4af37; margin:0;">✅ Uspešno ste zakazali!</h2>
            <p><strong>Usluga:</strong> {detalji['usluga']}</p>
            <p><strong>Datum:</strong> {formatiraj_datum(detalji['datum'])}</p>
            <p><strong>Vreme:</strong> {detalji['vreme']}</p>
            <p><strong>Trajanje:</strong> {detalji['trajanje']} min</p>
            <p><strong>Cena:</strong> {detalji['cena']} din</p>
            <p><strong>Klijent:</strong> {detalji['ime']}</p>
            <p style="margin-top:15px; font-size:1.2em; color:#d4af37;">✂️ Vidimo se!</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📅 Zakaži novi termin"):
            st.session_state['booking_success'] = False
            st.rerun()
    else:
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        datumi_raw = generisi_datume()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
        usluge = c.fetchall()
        conn.close()
        
        if datumi_raw and usluge:
            with st.form("klijent_forma"):
                ime = st.text_input("Ime i prezime *")
                tel = st.text_input("Telefon *")
                
                usluga_opcije = [f"{u[0]} ({u[2]} min, {u[1]} din)" for u in usluge]
                izabrana = st.selectbox("Usluga", usluga_opcije)
                
                idx = usluga_opcije.index(izabrana) if izabrana in usluga_opcije else 0
                usluga_ime = usluge[idx][0]
                usluga_cena = usluge[idx][1]
                usluga_trajanje = usluge[idx][2]
                
                datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
                
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT vreme, ime FROM rezervacije WHERE datum=? ORDER BY vreme ASC", (datum,))
                svi_slotovi = c.fetchall()
                conn.close()
                
                slobodni_termini = []
                for vreme, ime_slota in svi_slotovi:
                    if ime_slota is None and dovoljno_slobodnih_slotova(datum, vreme, usluga_trajanje):
                        slobodni_termini.append(vreme)
                
                if slobodni_termini:
                    termin = st.selectbox("Slobodan termin", slobodni_termini)
                    
                    if st.form_submit_button("Zakaži"):
                        if rezervisi_blok(datum, termin, usluga_trajanje, ime, tel, usluga_ime, usluga_cena):
                            st.session_state['booking_success'] = True
                            st.session_state['booking_details'] = {
                                'usluga': usluga_ime,
                                'datum': datum,
                                'vreme': termin,
                                'trajanje': usluga_trajanje,
                                'cena': usluga_cena,
                                'ime': ime
                            }
                            st.rerun()
                        else:
                            st.error("❌ Greška pri rezervaciji. Pokušajte ponovo.")
                else:
                    st.warning("⏳ Nema dovoljno slobodnih termina za ovu uslugu na izabrani datum.")
        else:
            st.error("❌ Baza je prazna.")

# ===================================================================
# TAB 2: ADMIN
# ===================================================================
with tab2:
    if "admin" not in st.session_state:
        st.session_state.admin = False
    
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Očisti sve termine (reset)"):
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0")
                conn.commit()
                conn.close()
                st.success("✅ Svi termini su očišćeni!")
                st.rerun()
        with col2:
            if st.button("🔄 Ručno generiši slotove"):
                osvezi_termine()
                st.success("✅ Slotovi su regenerisani!")
                st.rerun()
        
        st.divider()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        c.execute("SELECT count(*) FROM rezervacije WHERE datum=? AND ime IS NOT NULL", (today,))
        danas_klijenata = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM rezervacije WHERE ime IS NOT NULL AND (naplaceno IS NULL OR naplaceno=0)")
        nenaplaceno = c.fetchone()[0]
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Danas", f"{danas_klijenata} klijenata")
        with col2:
            st.metric("⏳ Čeka naplatu", f"{nenaplaceno}")
        
        st.subheader("📊 Finansijski izveštaj")
        
        this_month = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate=?", (today,))
        danas_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{this_month}%",))
        mesec_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        ukupno_promet = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 Danas", f"{danas_promet} din")
        with col2:
            st.metric("📆 Ovaj mesec", f"{mesec_promet} din")
        with col3:
            st.metric("💰 Ukupno", f"{ukupno_promet} din")
        
        st.subheader("📈 Promet po mesecima")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(datum_naplate,1,7) FROM rezervacije WHERE naplaceno=1 AND datum_naplate IS NOT NULL ORDER BY datum_naplate DESC")
        dostupni_meseci = [row[0] for row in c.fetchall()]
        conn.close()
        
        if dostupni_meseci:
            izabrani_mesec = st.selectbox("Izaberite mesec", dostupni_meseci, index=0)
            
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{izabrani_mesec}%",))
            promet_mesec = c.fetchone()[0] or 0
            conn.close()
            
            st.write(f"### Promet za {izabrani_mesec}: **{promet_mesec} din**")
        else:
            st.info("📭 Još uvek nema naplaćenih usluga.")
        
        st.subheader("📋 Zakazani klijenti")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, ime, telefon, usluga, datum, vreme, cena, naplaceno 
            FROM rezervacije 
            WHERE ime IS NOT NULL 
            ORDER BY datum ASC, vreme ASC
        """)
        svi_klijenti = c.fetchall()
        conn.close()
        
        if svi_klijenti:
            for idx, red in enumerate(svi_klijenti, start=1):
                id, ime, telefon, usluga, datum, vreme, cena, naplaceno = red
                
                st.markdown(f"""
                <div class="klijent-kartica">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <span style="color: #d4af37; font-weight: bold;">#{idx}</span>
                            <span style="color: #ffffff; font-weight: bold;">{ime}</span>
                            <span style="color: #d0d0d0;">📞 {telefon}</span>
                            <span style="color: #d0d0d0;">✂️ {usluga}</span>
                            <span style="color: #d0d0d0;">📅 {formatiraj_datum(datum)}</span>
                            <span style="color: #d0d0d0;">⏰ {vreme}</span>
                            <span style="color: #d4af37; font-weight: bold;">{cena} din</span>
                        </span>
                        <span>
                """, unsafe_allow_html=True)
                
                if naplaceno == 1:
                    st.markdown('<span style="color: #4ac24a;">✅ Naplaćeno</span>', unsafe_allow_html=True)
                else:
                    if st.button(f"💰 Naplati", key=f"pay_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE rezervacije SET naplaceno=1, datum_naplate=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), id))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Naplaćeno: {ime}")
                        st.rerun()
                    if st.button(f"🗑️ Otkaži", key=f"cancel_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0 WHERE id=?", (id,))
                        conn.commit()
                        conn.close()
                        st.success(f"🗑️ Otkazano: {ime}")
                        st.rerun()
                
                st.markdown("""
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 Trenutno nema zakazanih klijenata.")
        
        # ---------- UPRAVLJANJE USLUGAMA (tabelarni prikaz sa zlatnim linijama) ----------
        st.subheader("📝 Upravljanje uslugama")
        
        # Dodavanje nove usluge
        with st.form("dodaj_uslugu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nova_usluga = st.text_input("Naziv nove usluge")
            with col2:
                nova_cena = st.number_input("Cena (din)", min_value=0, step=100)
            with col3:
                if st.form_submit_button("➕ Dodaj"):
                    if nova_usluga and nova_cena > 0:
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)", (nova_usluga, nova_cena, 60))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Dodato: {nova_usluga} - {nova_cena} din")
                        st.rerun()
        
        # Tabelarni prikaz svih usluga sa zlatnim linijama
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY usluga")
        sve_usluge = c.fetchall()
        conn.close()
        
        if sve_usluge:
            st.markdown("""
            <table class="usluge-tabela">
                <tr>
                    <th>Usluga</th>
                    <th>Cena (din)</th>
                    <th>Trajanje (min)</th>
                    <th>Akcija</th>
                </tr>
            """, unsafe_allow_html=True)
            
            for usluga, cena, trajanje in sve_usluge:
                st.markdown(f"""
                <tr>
                    <td><strong>{usluga}</strong></td>
                    <td>{cena}</td>
                    <td>{trajanje}</td>
                    <td>
                        <form action="#" method="post">
                            <input type="number" name="nova_cena_{usluga}" value="{cena}" step="100" style="width:80px;">
                            <input type="number" name="novo_trajanje_{usluga}" value="{trajanje}" step="15" style="width:60px;">
                            <button type="submit" style="background-color:#d4af37; color:#1a1a1a; border:none; border-radius:12px; padding:4px 12px;">💾 Sačuvaj</button>
                        </form>
                    </td>
                </tr>
                """, unsafe_allow_html=True)
            
            st.markdown("</table>", unsafe_allow_html=True)
            
            # Ručna obrada za dugmad (pošto Streamlit ne podržava forme u tabelama)
            # Ovo je rešeno preko standardnih Streamlit widget-a ispod tabele
            st.write("---")
            st.write("**Izmena postojećih usluga:**")
            
            for usluga, cena, trajanje in sve_usluge:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{usluga}**")
                with col2:
                    st.write(f"{cena} din")
                with col3:
                    novo_trajanje = st.number_input(f"Trajanje (min)", value=trajanje, step=15, key=f"trajanje_{usluga}")
                with col4:
                    nova_cena = st.number_input(f"Nova cena", value=cena, step=100, key=f"cena_{usluga}")
                    if st.button(f"💾 Sačuvaj", key=f"save_{usluga}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE cenovnik SET cena=?, trajanje=? WHERE usluga=?", (nova_cena, novo_trajanje, usluga))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Usluga {usluga} ažurirana!")
                        st.rerun()
        else:
            st.info("📭 Trenutno nema definisanih usluga.")
