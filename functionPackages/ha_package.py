
def generate_ha_db_tables(db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""CREATE TABLE if not exists weatherStation (
                 room text, date text, time text,  temp text, humidity text, pressure, moisture text)""")
        db_cursor.execute("""CREATE TABLE if not exists econsumption (
                 date text, consumption text)""")
        db_cursor.execute("""CREATE TABLE if not exists prep (
                 id text, item_name text,  quantity text, expiry_date text)""")
        db_cursor.execute("""CREATE TABLE if not exists settings (
                        room text, description text)""")
        db_cursor.execute("""CREATE TABLE if not exists lights (
                                id text, ip text, val1 text, val2 text, val3 text, state text)""")
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def add_data_to_ha_db(db_cursor, db_connection, room, date, time, temp, humidity, pressure, moisture, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""INSERT INTO weatherStation VALUES(?, ?, ?, ?, ?, ?, ?)""", (room, date, time, temp,
                                                                                      humidity, pressure, moisture))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def add_econsumption_data(date, value, db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""INSERT INTO econsumption VALUES(?, ?)""", (date, value))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def rename_room(room_number: str, new_name: str, db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("UPDATE settings SET description = ? WHERE room = ?", (new_name, room_number,))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def get_prep_data(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM prep """)
    prep_data = [list(x) for x in db_cursor.fetchall()]
    lock.release()
    prep_data = sorted(prep_data, key=lambda x: x[4])
    return prep_data


def add_prep_data(id_number, item, itemType,  quantity, date, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""INSERT INTO prep VALUES(?, ?, ?, ?, ?)""", (id_number, item, itemType, quantity, date))
    db_connection.commit()
    lock.release()
    return None


def delete_prep_data(id_number, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("""DELETE FROM prep where id = ?""", (id_number, ))
    db_connection.commit()
    lock.release()
    return None


def get_light_vals(db_cursor, lock):
    lock.acquire(True)
    db_cursor.execute("""SELECT * FROM lights """)
    lights = [list(x) for x in db_cursor.fetchall()]
    lock.release()
    return lights


def add_val_to_light(light_id, val_id, val, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("UPDATE lights SET val"+val_id+" = ? WHERE id = ?", (val, light_id, ))
    db_connection.commit()
    lock.release()


def switch_light(light_id, state, db_cursor, db_connection, lock):
    lock.acquire(True)
    db_cursor.execute("UPDATE lights SET state = ? WHERE id = ?", (state, light_id, ))
    db_connection.commit()
    lock.release()