import csv
import os
from collections import Counter

DATA_DIR = '../data'
FILES = [
    'DoS_dataset.csv',
    'Fuzzy_dataset.csv',
    'spoofing_gear_dataset.csv',
    'normal_run_data.txt'
]

def validate_file(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"[{filename}] ERROR: File not found.")
        return

    row_count = 0
    malformed_count = 0
    class_balance = Counter()

    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            row_count += 1
            if len(row) != 12:
                malformed_count += 1
                continue
            
            flag = row[-1]
            if flag not in ['R', 'T']:
                malformed_count += 1
                continue
            
            class_balance[flag] += 1

    print(f"--- {filename} ---")
    print(f"Total Rows: {row_count}")
    print(f"Malformed Rows: {malformed_count}")
    print(f"Class Balance: Normal (R): {class_balance['R']}, Attack (T): {class_balance['T']}")
    print()

if __name__ == '__main__':
    for file in FILES:
        validate_file(file)
