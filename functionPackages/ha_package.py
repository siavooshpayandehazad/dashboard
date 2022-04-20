
def generate_ha_db_tables(db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""CREATE TABLE if not exists weatherStation (
                 room text, date text, time text,  temp text, humidity text, pressure, moisture text)""")
        db_cursor.execute("""CREATE TABLE if not exists econsumption (
                 date text, consumption text)""")
        db_cursor.execute("""CREATE TABLE if not exists settings (
                 room text, description text)""")
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
