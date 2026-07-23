import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta

# ---------- STIL ----------
st.markdown("""
<style>
    .stApp { background-color: #4a4a4a; color: #e0e0e0; }
    h1, h2, h3 { color: #d4af37 !important; }
    .stButton button {
        background-color: #d4af37 !important;
        color: #1a1a1a !important;
        font-weight: bold !important;
        border-radius: 20px !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton button:hover { background-color: #e6c86a !important; transform: scale(1.02); }
    .stMetric {
        background-color: #3a3a3a;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid #d4af37;
        color: #e0e0e0;
    }
    .stMetric label, .stMetric div { color: #e0e0e0 !important; }
    .stSelectbox, .stTextInput, .stNumberInput {
        background-color: #3a3a3a !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #d4af37 !important;
    }
    .stSelectbox input, .stTextInput input, .stNumberInput input {
        color: #ffffff !important;
        background-color: #3a3a3a !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #d0d0d0 !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #3a3a3a !important;
        color: #ffffff !important;
    }
    .form-container {
        border: 2px solid #d4af37;
        border-radius: 16px;
        padding: 20px;
        background-color: #3a3a3a;
        margin: 10px 0;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
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
    .slot-slobodan {
        background-color: #2a7a2a !important;
        color: white !important;
        border: 1px solid #4ac24a !important;
        border-radius: 8px !important;
        padding: 8px 0 !important;
        width: 100% !important;
        font-weight: bold !important;
        transition: 0.2s;
        cursor: pointer;
    }
    .slot-slobodan:hover {
        background-color: #3a9a3a !important;
        transform: scale(1.02);
    }
    .slot-zauzet {
        background-color: #7a2a2a !important;
        color: #aaaaaa !important;
        border: 1px solid #aa4a4a !important;
        border-radius: 8px !important;
        padding: 8px 0 !important;
        width: 100% !important;
        font-weight: bold !important;
        cursor: not-allowed !important;
        opacity: 0.7;
    }
    .slot-nedovoljno {
        background-color: #5a4a3a !important;
        color: #888888 !important;
        border: 1px solid #6a5a4a !important;
        border-radius: 8px !important;
        padding: 8px 0 !important;
        width: 100% !important;
        font-weight: bold !important;
        cursor: not-allowed !important;
        opacity: 0.6;
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
        if dan.weekday() != 6:
            datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_slotove_za_dan(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:
        return
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM rezervacije WHERE datum=?", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    c.execute("SELECT vreme FROM pauze WHERE datum=?", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    for i in range(PAUZA_POCETAK*4, PAUZA_KRAJ*4):
        vreme = f"{i//4:02d}:{(i%4)*15:02d}"
        if vreme not in pauze:
            pauze.append(vreme)
    
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
        SELECT vreme, ime FROM rezervacije 
        WHERE datum=? AND vreme >= ? 
        ORDER BY vreme ASC LIMIT ?
    """, (datum, pocetak, broj_slotova))
    
    slotovi = c.fetchall()
    
    if len(slotovi) < broj_slotova:
        conn.close()
        return False
    
    for vreme, ime_slota in slotovi:
        if ime_slota is not None:
            conn.close()
            return False
    
    vremena = [row[0] for row in slotovi]
    for i in range(broj_slotova - 1):
        t1 = datetime.strptime(vremena[i], "%H:%M")
        t2 = datetime.strptime(vremena[i+1], "%H:%M")
        if (t2 - t1).seconds // 60 != INTERVAL_MIN:
            conn.close()
            return False
    
    for vreme in vremena:
        c.execute("SELECT id FROM rezervacije WHERE datum=? AND vreme=?", (datum, vreme))
        id = c.fetchone()[0]
        c.execute("""
            UPDATE rezervacije 
            SET ime=?, telefon=?, usluga=?, cena=?, naplaceno=0 
            WHERE id=?
        """, (ime, telefon, usluga, cena, id))
    
    conn.commit()
    conn.close()
    return True

# ---------- FUNKCIJA ZA PRIKAZ TABELE TERMINA ----------
def prikazi_tabelu_termina(datum, usluga_trajanje, mode="klijent"):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT vreme, ime FROM rezervacije 
        WHERE datum=? 
        ORDER BY vreme ASC
    """, (datum,))
    svi_slotovi = c.fetchall()
    conn.close()
    
    if not svi_slotovi:
        st.warning("⏳ Nema slobodnih termina za izabrani datum.")
        return None
    
    jedinstveni = {}
    for vreme, ime in svi_slotovi:
        if vreme not in jedinstveni:
            jedinstveni[vreme] = ime
    
    svi_slotovi = list(jedinstveni.items())
    svi_slotovi.sort()
    
    cols_per_row = 4
    rows = [svi_slotovi[i:i+cols_per_row] for i in range(0, len(svi_slotovi), cols_per_row)]
    
    kliknuto_vreme = None
    
    for row in rows:
        cols = st.columns(cols_per_row)
        for j, (vreme, ime_slota) in enumerate(row):
            with cols[j]:
                if ime_slota is None:
                    if dovoljno_slobodnih_slotova(datum, vreme, usluga_trajanje):
                        if st.button(f"🟢 {vreme}", key=f"{mode}_slot_{datum}_{vreme}", use_container_width=True):
                            kliknuto_vreme = vreme
                    else:
                        st.markdown(f"""
                        <div class="slot-nedovoljno" style="text-align:center; padding:8px 0; border-radius:8px;">
                            {vreme}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="slot-zauzet" style="text-align:center; padding:8px 0; border-radius:8px;">
                        🔴 {vreme}
                    </div>
                    """, unsafe_allow_html=True)
    
    return kliknuto_vreme

# ---------- UI ----------
st.set_page_config(page_title="💈 Zakazivanje", layout="centered")

try:
    st.image("IMG-7dca0f9a0a28a9b8098a0cf36f04adb2-V.jpg", use_container_width=True)
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
            osvezi_termine()
            
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            
            ime = st.text_input("Ime i prezime *")
            tel = st.text_input("Telefon *")
            
            usluga_opcije = [f"{u[0]} ({u[2]} min, {u[1]} din)" for u in usluge]
            izabrana = st.selectbox("Usluga", usluga_opcije)
            
            idx = usluga_opcije.index(izabrana) if izabrana in usluga_opcije else 0
            usluga_ime = usluge[idx][0]
            usluga_cena = usluge[idx][1]
            usluga_trajanje = usluge[idx][2]
            
            datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
            
            st.subheader("📋 Slobodni termini")
            
            kliknuto_vreme = prikazi_tabelu_termina(datum, usluga_trajanje, mode="klijent")
            
            if kliknuto_vreme:
                if rezervisi_blok(datum, kliknuto_vreme, usluga_trajanje, ime, tel, usluga_ime, usluga_cena):
                    st.session_state['booking_success'] = True
                    st.session_state['booking_details'] = {
                        'usluga': usluga_ime,
                        'datum': datum,
                        'vreme': kliknuto_vreme,
                        'trajanje': usluga_trajanje,
                        'cena': usluga_cena,
                        'ime': ime
                    }
                    st.rerun()
                else:
                    st.error("❌ Greška pri rezervaciji. Pokušajte ponovo.")
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
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
        
        c.execute("""
            SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || datum || '|' || usluga) 
            FROM rezervacije 
            WHERE datum=? AND ime IS NOT NULL
        """, (today,))
        danas_klijenata = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM rezervacije WHERE ime IS NOT NULL AND (naplaceno IS NULL OR naplaceno=0)")
        nenaplaceno = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Danas", f"{danas_klijenata} klijenata")
        with col2:
            st.metric("⏳ Nenaplaćeni slotovi", f"{nenaplaceno}")
        
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
        
        # ---------- TABELA TERMINA ZA ADMINA ----------
        st.subheader("📋 Pregled termina (admin)")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        datumi_raw = generisi_datume()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
        usluge = c.fetchall()
        conn.close()
        
        if datumi_raw and usluge:
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            
            admin_ime = st.text_input("Ime klijenta *", key="admin_ime")
            admin_tel = st.text_input("Telefon klijenta *", key="admin_tel")
            
            admin_usluga_opcije = [f"{u[0]} ({u[2]} min, {u[1]} din)" for u in usluge]
            admin_izabrana = st.selectbox("Usluga", admin_usluga_opcije, key="admin_usluga")
            
            admin_idx = admin_usluga_opcije.index(admin_izabrana) if admin_izabrana in admin_usluga_opcije else 0
            admin_usluga_ime = usluge[admin_idx][0]
            admin_usluga_cena = usluge[admin_idx][1]
            admin_usluga_trajanje = usluge[admin_idx][2]
            
            admin_datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum, key="admin_datum")
            
            st.write("**Kliknite na zeleni termin da biste ga rezervisali:**")
            
            kliknuto_admin_vreme = prikazi_tabelu_termina(admin_datum, admin_usluga_trajanje, mode="admin")
            
            if kliknuto_admin_vreme:
                if admin_ime and admin_tel:
                    if rezervisi_blok(admin_datum, kliknuto_admin_vreme, admin_usluga_trajanje, admin_ime, admin_tel, admin_usluga_ime, admin_usluga_cena):
                        st.success(f"✅ Uspešno zakazano za {admin_ime} u {kliknuto_admin_vreme}!")
                        st.rerun()
                    else:
                        st.error("❌ Greška pri rezervaciji. Pokušajte ponovo.")
                        st.rerun()
                else:
                    st.warning("⚠️ Popunite ime i telefon klijenta pre nego što kliknete na termin.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ---------- ZAKAZANI KLIJENTI ----------
        st.subheader("📋 Zakazani klijenti")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("""
            SELECT ime, telefon, usluga, cena, datum, 
                   MIN(vreme) as pocetak, MAX(vreme) as kraj,
                   GROUP_CONCAT(id) as ids,
                   COUNT(*) as broj_slotova
            FROM rezervacije 
            WHERE ime IS NOT NULL 
            GROUP BY ime, telefon, datum, usluga, cena
            ORDER BY datum ASC, pocetak ASC
        """)
        grupe = c.fetchall()
        conn.close()
        
        if grupe:
            for idx, red in enumerate(grupe, start=1):
                ime, telefon, usluga, cena, datum, pocetak, kraj, ids, broj_slotova = red
                
                t1 = datetime.strptime(pocetak, "%H:%M")
                t2 = datetime.strptime(kraj, "%H:%M")
                trajanje = (t2 - t1).seconds // 60 + INTERVAL_MIN
                
                st.markdown(f"""
                <div class="klijent-kartica">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <span style="color: #d4af37; font-weight: bold;">#{idx}</span>
                            <span style="color: #ffffff; font-weight: bold;">{ime}</span>
                            <span style="color: #d0d0d0;">📞 {telefon}</span>
                            <span style="color: #d0d0d0;">✂️ {usluga}</span>
                            <span style="color: #d0d0d0;">📅 {formatiraj_datum(datum)}</span>
                            <span style="color: #d0d0d0;">⏰ {pocetak} - {kraj} ({trajanje} min)</span>
                            <span style="color: #d4af37; font-weight: bold;">{cena} din</span>
                        </span>
                        <span>
                """, unsafe_allow_html=True)
                
                first_id = int(ids.split(',')[0])
                conn2 = sqlite3.connect('termini.db')
                c2 = conn2.cursor()
                c2.execute("SELECT naplaceno FROM rezervacije WHERE id=?", (first_id,))
                naplaceno = c2.fetchone()[0]
                conn2.close()
                
                if naplaceno == 1:
                    st.markdown('<span style="color: #4ac24a;">✅ Naplaćeno</span>', unsafe_allow_html=True)
                else:
                    if st.button(f"💰 Naplati", key=f"pay_{idx}"):
                        conn3 = sqlite3.connect('termini.db')
                        c3 = conn3.cursor()
                        for id in ids.split(','):
                            c3.execute("UPDATE rezervacije SET naplaceno=1, datum_naplate=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), int(id)))
                        conn3.commit()
                        conn3.close()
                        st.success(f"✅ Naplaćeno: {ime}")
                        st.rerun()
                    if st.button(f"🗑️ Otkaži", key=f"cancel_{idx}"):
                        conn4 = sqlite3.connect('termini.db')
                        c4 = conn4.cursor()
                        for id in ids.split(','):
                            c4.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0 WHERE id=?", (int(id),))
                        conn4.commit()
                        conn4.close()
                        st.success(f"🗑️ Otkazano: {ime}")
                        st.rerun()
                
                st.markdown("""
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 Trenutno nema zakazanih klijenata.")
        
        # ---------- UPRAVLJANJE USLUGAMA ----------
        st.subheader("📝 Upravljanje uslugama")
        
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
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY usluga")
        sve_usluge = c.fetchall()
        conn.close()
        
        if sve_usluge:
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
