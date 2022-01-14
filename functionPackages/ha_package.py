
def generate_ha_DBTables(DBCursor, dbConnection, lock):
    try:
        lock.acquire(True)
        DBCursor.execute("""CREATE TABLE if not exists weatherStation (
                 room text, date text, time text,  temp text, humidity text, pressure text)""")
        DBCursor.execute("""CREATE TABLE if not exists econsumption (
                 date text, consumption text)""")
        DBCursor.execute("""CREATE TABLE if not exists settings (
                 room text, description text)""")
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def add_data_to_ha_DB(DBCursor, dbConnection, room, date, time, temp, humidity, pressure, lock):
    try:
        lock.acquire(True)
        DBCursor.execute("""INSERT INTO weatherStation VALUES(?, ?, ?, ?, ?, ?)""", (room, date, time, temp, humidity, pressure))
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def add_econsumption_data(date, value, DBCursor, dbConnection, lock):
    try:
        lock.acquire(True)
        DBCursor.execute("""INSERT INTO econsumption VALUES(?, ?)""", (date, value))
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def rename_room(roomNumber: str, newName: str, DBCursor, dbConnection, lock):
    try:
        lock.acquire(True)
        DBCursor.execute("""DELETE FROM settings WHERE room = ? """, (roomNumber))
        DBCursor.execute("""INSERT INTO settings VALUES(?, ?)""", (roomNumber, newName))
        dbConnection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False
