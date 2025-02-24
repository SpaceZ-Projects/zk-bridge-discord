
import os
import sqlite3

group_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "group.dat")

class Storage():
    def __init__(self):
        super().__init__()

    def is_exists(self):
        if not os.path.exists(group_data):
            return False
        return True

    def identity(self, category, username, address, channel_id):
        self.create_identity_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO identity (category, username, address, channel)
            VALUES (?, ?, ?, ?)
            ''', 
            (category, username, address, channel_id)
        )
        conn.commit()
        conn.close()


    def key(self, prv_key):
        self.create_key_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO key (prv_key)
            VALUES (?)
            ''', 
            (prv_key,)
        )
        conn.commit()
        conn.close()


    def tx(self, txid):
        self.create_txs_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO txs (txid)
            VALUES (?)
            ''', 
            (txid,)
        )
        conn.commit()
        conn.close()


    def add_contact(self, category, id, contact_id, username, address):
        self.create_contacts_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO contacts (category, id, contact_id, username, address)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (category, id, contact_id, username, address)
        )
        conn.commit()
        conn.close()

    
    def add_pending(self, category, id, username, address):
        self.create_pending_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO pending (category, id, username, address)
            VALUES (?, ?, ?, ?)
            ''',
            (category, id, username, address)
        )
        conn.commit()
        conn.close()


    def message(self, id, author, message, amount, message_id, timestamp):
        self.create_messages_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO messages (id, author, message, amount, message_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', 
            (id, author, message, amount, message_id, timestamp)
        )
        conn.commit()
        conn.close()


    def ban(self, address):
        self.create_banned_table()
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO banned (address)
            VALUES (?)
            ''', 
            (address,)
        )
        conn.commit()
        conn.close()


    def get_key(self):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT prv_key FROM key"
            )
            result = cursor.fetchone()
            conn.close()
            return result
        except sqlite3.OperationalError:
            return None
        

    def get_identity(self, option = None):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            if option == "address":
                cursor.execute(
                    "SELECT address FROM identity"
                )
                result = cursor.fetchone()
            elif option == "channel":
                cursor.execute(
                    "SELECT channel FROM identity"
                )
                result = cursor.fetchone()
            elif option is None:
                cursor.execute(
                    "SELECT category, username, address FROM identity"
                )
                result = cursor.fetchone()
            conn.close()
            return result
        except sqlite3.OperationalError:
            return None
        

    def get_contacts(self, option = None):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM contacts')
            contacts = cursor.fetchall()
            conn.close()
            return contacts
        except sqlite3.OperationalError:
            return []
        

    def get_contact_username(self, contact_id):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT username FROM contacts WHERE contact_id = ?',
                (contact_id,)
            )
            contact = cursor.fetchone()
            conn.close()
            return contact
        except sqlite3.OperationalError:
            return None
        

    def get_txs(self):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute('SELECT txid FROM txs')
            txs = [row[0] for row in cursor.fetchall()]
            conn.close()
            return txs
        except sqlite3.OperationalError:
            return []
        

    def get_messages(self):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM messages')
            messages = cursor.fetchall()
            conn.close()
            return messages
        except sqlite3.OperationalError:
            return []
        

    def delete_message(self, message_id):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute(
                '''
                DELETE FROM messages WHERE message_id = ?
                ''', 
                (message_id,)
            )
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Error deleting message: {e}")
        

    def get_banned(self):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute('SELECT address FROM banned')
            txs = [row[0] for row in cursor.fetchall()]
            conn.close()
            return txs
        except sqlite3.OperationalError:
            return []
        

    def get_pending(self, option = None):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            if option == "address":
                cursor.execute("SELECT address FROM pending")
                contacts = [row[0] for row in cursor.fetchall()]
            elif option is None:
                cursor.execute('SELECT * FROM pending')
                contacts = cursor.fetchall()
            conn.close()
            return contacts
        except sqlite3.OperationalError:
            return []
        

    def delete_contact(self, address):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute(
                '''
                DELETE FROM contacts WHERE address = ?
                ''', 
                (address,)
            )
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Error deleting contact: {e}")


    def edit_username(self, old_username, new_username):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE identity
            SET username = ?
            WHERE username = ?
            ''', (new_username, old_username)
        )
        conn.commit()
        conn.close()


    def update_contact_username(self, username, contact_id):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            UPDATE contacts
            SET username = ?
            WHERE contact_id = ?
            ''', (username, contact_id)
        )
        conn.commit()
        conn.close()


    def delete_pending(self, address):
        try:
            conn = sqlite3.connect(group_data)
            cursor = conn.cursor()
            cursor.execute(
                '''
                DELETE FROM pending WHERE address = ?
                ''', 
                (address,)
            )
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Error deleting pending contact: {e}")


    def create_identity_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS identity (
                category TEXT,
                username TEXT,
                address TEXT,
                channel INTEGER
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_key_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS key (
                prv_key TEXT
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_txs_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS txs (
                txid TEXT
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_contacts_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS contacts (
                category TEXT,
                id TEXT,
                contact_id TEXT,
                username TEXT,
                address TEXT
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_messages_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT,
                author TEXT,
                message TEXT,
                amount REAL,
                message_id INTEGER,
                timestamp INTEGER
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_banned_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS banned (
                address TEXT
            )
            '''
        )
        conn.commit()
        conn.close()


    def create_pending_table(self):
        conn = sqlite3.connect(group_data)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS pending (
                category TEXT,
                id TEXT,
                username TEXT,
                address TEXT
            )
            '''
        )
        conn.commit()
        conn.close()
