import streamlit as st
import psycopg2
import os
from datetime import datetime, timedelta

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 15
BROJ_DANA = 7
PAUZA_POCETAK = 12
PAUZA_KRAJ = 13

# ---------- POSTGRESQL VEZA ----------
# 🔥 OVDE NALEPI SVOJ CONNECTION STRING
DATABASE_URL = "postgresql://postgres.ilmgdtpusrlexlvjiotx:tatarista1199111@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ---------- INICIJALIZACIJA BAZE ----------
def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije (
                 id SERIAL PRIMARY KEY, 
                 usluga TEXT, 
                 datum TEXT, 
                 vreme TEXT, 
                 ime TEXT, 
                 telefon TEXT, 
                 cena INTEGER, 
                 naplaceno INTEGER DEFAULT 0, 
                 datum_naplate TEXT)''')
    
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
    for u in usluge:
        c.execute("INSERT INTO cenovnik (usluga, cena, trajanje) VALUES (%s, %s, %s) ON CONFLICT (usluga) DO NOTHING", u)
    
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS pauze (
                 id SERIAL PRIMARY KEY, 
                 datum TEXT, 
                 vreme TEXT, 
                 napomena TEXT)''')
    
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
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("DELETE FROM rezervacije WHERE datum=%s AND ime IS NULL", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    c.execute("SELECT vreme FROM pauze WHERE datum=%s", (datum_str,))
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
        for s in slotovi:
            c.execute("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, naplaceno, datum_naplate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", s)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_slotove_za_dan(d)
    return True

def rezervisi_blok(datum, pocetak, trajanje, ime, telefon, usluga, cena):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, naplaceno, datum_naplate)
        VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
    """, (usluga, datum, pocetak, ime, telefon, cena, None))
    
    conn.commit()
    conn.close()
    
    conn2 = get_db()
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) FROM rezervacije WHERE ime=%s AND datum=%s AND vreme=%s", (ime, datum, pocetak))
    count = c2.fetchone()[0]
    conn2.close()
    
    return count > 0

def prikazi_tabelu_termina(datum, usluga_trajanje):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT vreme, ime FROM rezervacije 
        WHERE datum=%s 
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
                if ime_slota is None or ime_slota == "":
                    if st.button(f"🟢 {vreme}", key=f"slot_{datum}_{vreme}", use_container_width=True):
                        kliknuto_vreme = vreme
                else:
                    st.markdown(f"""
                    <div style="background-color:#7a2a2a; color:#aaaaaa; border:1px solid #aa4a4a; border-radius:8px; padding:8px 0; text-align:center; width:100%; font-weight:bold; cursor:not-allowed; opacity:0.7;">
                        🔴 {vreme}
                    </div>
                    """, unsafe_allow_html=True)
    
    return kliknuto_vreme

# ---------- UI ----------
st.set_page_config(page_title="💈 Zakazivanje", layout="centered")

st.title("💈 Berberski salon - Zakazivanje")

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

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
        conn = get_db()
        c = conn.cursor()
        datumi_raw = generisi_datume()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
        usluge = c.fetchall()
        conn.close()
        
        if datumi_raw and usluge:
            osvezi_termine()
            
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
            
            st.markdown("""
            <div style="display: flex; gap: 10px; margin: 5px 0; font-size: 0.9em;">
                <span>🟢 <span style="color: #aaa;">Slobodan termin</span></span>
                <span>🔴 <span style="color: #aaa;">Zauzet termin</span></span>
            </div>
            """, unsafe_allow_html=True)
            
            kliknuto_vreme = prikazi_tabelu_termina(datum, usluga_trajanje)
            
            if kliknuto_vreme:
                if ime and tel:
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
                else:
                    st.warning("⚠️ Popunite ime i telefon pre nego što kliknete na termin.")
        else:
            st.error("❌ Baza je prazna.")

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
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0")
                conn.commit()
                conn.close()
                st.success("✅ Svi termini su očišćeni!")
                st.rerun()
        with col2:
            if st.button("🔄 Ručno generiši slotove"):
                if osvezi_termine():
                    st.success("✅ Slotovi su regenerisani!")
                    st.rerun()
                else:
                    st.error("❌ Greška pri generisanju slotova.")
                    st.rerun()
        
        st.divider()
        
        # 🔥 DEBUG
        st.subheader("🔍 DEBUG - Svi podaci iz baze")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM rezervacije ORDER BY datum, vreme")
        svi = c.fetchall()
        if svi:
            st.write("📋 Svi redovi u bazi:")
            for red in svi:
                st.write(red)
        else:
            st.info("📭 Baza je prazna.")
        conn.close()
        st.divider()
        
        conn = get_db()
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        c.execute("""
            SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || datum || '|' || usluga) 
            FROM rezervacije 
            WHERE datum=%s AND ime IS NOT NULL
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
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate=%s", (today,))
        danas_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE %s", (f"{this_month}%",))
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
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(datum_naplate,1,7) FROM rezervacije WHERE naplaceno=1 AND datum_naplate IS NOT NULL ORDER BY datum_naplate DESC")
        dostupni_meseci = [row[0] for row in c.fetchall()]
        conn.close()
        
        if dostupni_meseci:
            izabrani_mesec = st.selectbox("Izaberite mesec", dostupni_meseci, index=0)
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE %s", (f"{izabrani_mesec}%",))
            promet_mesec = c.fetchone()[0] or 0
            conn.close()
            
            st.write(f"### Promet za {izabrani_mesec}: **{promet_mesec} din**")
        else:
            st.info("📭 Još uvek nema naplaćenih usluga.")
        
        st.subheader("📋 Zakazani klijenti")
        
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT ime, telefon, usluga, cena, datum, 
                   MIN(vreme) as pocetak, MAX(vreme) as kraj,
                   array_agg(id) as ids,
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
                <div style="background-color:#3a3a3a; border-radius:12px; padding:12px 16px; margin:8px 0; border:2px solid #d4af37; box-shadow:0 2px 8px rgba(212,175,55,0.15);">
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
                
                first_id = ids[0]
                conn2 = get_db()
                c2 = conn2.cursor()
                c2.execute("SELECT naplaceno FROM rezervacije WHERE id=%s", (first_id,))
                naplaceno = c2.fetchone()[0]
                conn2.close()
                
                if naplaceno == 1:
                    st.markdown('<span style="color: #4ac24a;">✅ Naplaćeno</span>', unsafe_allow_html=True)
                else:
                    if st.button(f"💰 Naplati", key=f"pay_{idx}"):
                        conn3 = get_db()
                        c3 = conn3.cursor()
                        for id in ids:
                            c3.execute("UPDATE rezervacije SET naplaceno=1, datum_naplate=%s WHERE id=%s", (datetime.now().strftime("%Y-%m-%d"), id))
                        conn3.commit()
                        conn3.close()
                        st.success(f"✅ Naplaćeno: {ime}")
                        st.rerun()
                    if st.button(f"🗑️ Otkaži", key=f"cancel_{idx}"):
                        conn4 = get_db()
                        c4 = conn4.cursor()
                        for id in ids:
                            c4.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0 WHERE id=%s", (id,))
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
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("INSERT INTO cenovnik (usluga, cena, trajanje) VALUES (%s, %s, %s) ON CONFLICT (usluga) DO NOTHING", (nova_usluga, nova_cena, 60))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Dodato: {nova_usluga} - {nova_cena} din")
                        st.rerun()
        
        conn = get_db()
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
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("UPDATE cenovnik SET cena=%s, trajanje=%s WHERE usluga=%s", (nova_cena, novo_trajanje, usluga))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Usluga {usluga} ažurirana!")
                        st.rerun()
        else:
            st.info("📭 Trenutno nema definisanih usluga.")