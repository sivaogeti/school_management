import sqlite3
import pandas as pd

conn = sqlite3.connect('../data/school.db')

# Import users
df = pd.read_csv('users.csv')

# Rename columns if needed
if 'password_hash' in df.columns:
    df.rename(columns={'password_hash': 'password'}, inplace=True)

# Insert into table
df.to_sql('users', conn, if_exists='append', index=False)

conn.close()
print("✅ Sample data inserted")
