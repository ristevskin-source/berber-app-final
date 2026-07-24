def dovoljno_slobodnih_slotova(datum, pocetak, trajanje):
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    # Dohvati sve slobodne slotove od početka
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND ime IS NULL 
        ORDER BY vreme ASC
    """, (datum, pocetak))
    
    slobodni = [row[0] for row in c.fetchall()]
    conn.close()
    
    # Proveri da li ima dovoljno uzastopnih slotova
    if len(slobodni) < broj_slotova:
        return False
    
    for i in range(broj_slotova - 1):
        t1 = datetime.strptime(slobodni[i], "%H:%M")
        t2 = datetime.strptime(slobodni[i+1], "%H:%M")
        if (t2 - t1).seconds // 60 != INTERVAL_MIN:
            return False
    
    return True
