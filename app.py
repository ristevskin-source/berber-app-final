def dovoljno_slobodnih_slotova(datum, pocetak, trajanje):
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    # 🔥 Dohvati prvi slobodan slot OD IZABRANOG VREMENA
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC LIMIT 1
    """, (datum, pocetak))
    
    prvi = c.fetchone()
    
    if not prvi or prvi[0] != pocetak:
        conn.close()
        return False
    
    # 🔥 Dohvati sve slotove od tog vremena
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC LIMIT ?
    """, (datum, pocetak, broj_slotova))
    
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
    
    # 🔥 Dohvati slotove OD IZABRANOG VREMENA
    c.execute("""
        SELECT id, vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC LIMIT ?
    """, (datum, pocetak, broj_slotova))
    
    pronadjeni = c.fetchall()
    
    # 🔥 STROGA PROVERA: prvi slot MORA biti baš izabrani termin
    if len(pronadjeni) < broj_slotova:
        conn.close()
        return False
    
    if pronadjeni[0][1] != pocetak:
        conn.close()
        return False
    
    # Provera uzastopnosti
    for i in range(broj_slotova - 1):
        t1 = datetime.strptime(pronadjeni[i][1], "%H:%M")
        t2 = datetime.strptime(pronadjeni[i+1][1], "%H:%M")
        if (t2 - t1).seconds // 60 != INTERVAL_MIN:
            conn.close()
            return False
    
    # Ažuriraj
    ids = [row[0] for row in pronadjeni]
    for id in ids:
        c.execute("""
            UPDATE rezervacije 
            SET ime=?, telefon=?, usluga=?, cena=?, naplaceno=0 
            WHERE id=?
        """, (ime, telefon, usluga, cena, id))
    
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE ime=? AND datum=? AND vreme=?", (ime, datum, pocetak))
    count = c.fetchone()[0]
    conn.close()
    
    return count > 0
