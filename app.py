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
        
        # 🔥 BROJ JEDINSTVENIH KLIJENATA DANAS
        c.execute("""
            SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || datum || '|' || usluga) 
            FROM rezervacije 
            WHERE datum=? AND ime IS NOT NULL
        """, (today,))
        danas_klijenata = c.fetchone()[0] or 0
        
        # 🔥 BROJ NENAPLACENIH SLOTOVA (ukupno)
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
