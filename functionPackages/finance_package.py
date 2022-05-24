
def generate_finance_db_tables(db_cursor, db_connection, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""CREATE TABLE if not exists finance (
                 date text, name text, cost text, type text)""")
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False


def add_data_to_finance_db(db_cursor, db_connection, date, name, cost, expense_type, lock):
    try:
        lock.acquire(True)
        db_cursor.execute("""INSERT INTO finance VALUES(?, ?, ?, ?)""", (date, name, cost, expense_type))
        db_connection.commit()
        lock.release()
        return True
    except Exception as err:
        print(err)
        return False
