from yoyo import step


step("""
    CREATE TABLE messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        timestamp INTEGER NOT NULL,
        from_id INTEGER NOT NULL,
        from_name VARCHAR(255) NOT NULL,
        subject TEXT NOT NULL,
        body LONGTEXT NOT NULL
    );
""")

step("""
    CREATE TABLE message_recipient (
        message_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        recipient_name VARCHAR(255) NOT NULL,
        mailbox_index INTEGER,
        read INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (message_id, recipient_id)
    );
""")
