"""Check signals in database."""
import sqlite3

conn = sqlite3.connect('data/db/signalengine.db')
cursor = conn.cursor()

# Count all signals
cursor.execute('SELECT COUNT(*) FROM signals')
total = cursor.fetchone()[0]
print(f'Total signals: {total}')

# Count signals >= 0.60
cursor.execute('SELECT COUNT(*) FROM signals WHERE score >= 0.60')
high_score = cursor.fetchone()[0]
print(f'Signals with score >= 0.60: {high_score}')

# Count signals < 0.60
cursor.execute('SELECT COUNT(*) FROM signals WHERE score < 0.60')
low_score = cursor.fetchone()[0]
print(f'Signals with score < 0.60: {low_score}')

# Latest 10 signals
cursor.execute('SELECT symbol, direction, score, timestamp FROM signals ORDER BY timestamp DESC LIMIT 10')
print('\nLatest 10 signals:')
for row in cursor.fetchall():
    symbol, direction, score, ts = row
    print(f'  {symbol:12} {direction:5} score={score:.2f} ts={ts}')

# Check score distribution
cursor.execute('SELECT MIN(score), MAX(score), AVG(score) FROM signals')
min_s, max_s, avg_s = cursor.fetchone()
print(f'\nScore distribution:')
print(f'  Min: {min_s:.2f}')
print(f'  Max: {max_s:.2f}')
print(f'  Avg: {avg_s:.2f}')

conn.close()
