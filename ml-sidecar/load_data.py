import os
import re

import pandas as pd

DATA_DIR = '../data'
OUTPUT_FILE = 'processed_data.csv'

COLUMNS = ['Timestamp', 'CAN_ID', 'DLC', 'DATA0', 'DATA1', 'DATA2', 'DATA3', 'DATA4', 'DATA5', 'DATA6', 'DATA7', 'Flag']

DATASETS = {
    'normal_run_data/normal_run_data.txt': 0,
    'DoS_dataset.csv': 1,
    'Fuzzy_dataset.csv': 2,
    'gear_dataset.csv': 3
}

SAMPLE_SIZE_PER_FILE = 75000

def process_and_sample_file(filepath, attack_label, sample_size=SAMPLE_SIZE_PER_FILE):
    print(f"Processing {filepath}...")
    
    parsed_data = []
    
    is_space_format = 'normal_run_data.txt' in filepath and 'normal_run_data/' in filepath
    space_regex = re.compile(r"Timestamp:\s+([\d\.]+)\s+ID:\s+([0-9a-fA-F]+)\s+\d+\s+DLC:\s+(\d+)\s+(.*)")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if is_space_format:
                match = space_regex.search(line)
                if not match:
                    continue
                timestamp, can_id, dlc, data_str = match.groups()
                data = data_str.strip().split()
                flag = 'R'
            else:
                parts = line.strip().split(',')
                if len(parts) < 4:
                    continue
                timestamp = parts[0]
                can_id = parts[1]
                dlc = parts[2]
                flag = parts[-1]
                data = parts[3:-1]
                
            # Pad data to 8 bytes
            data = data + ['00'] * (8 - len(data))
            data = data[:8]
            
            parsed_data.append([timestamp, can_id, dlc] + data + [flag])
            
    df = pd.DataFrame(parsed_data, columns=COLUMNS)
    df['Timestamp'] = df['Timestamp'].astype(float)
    df['DLC'] = pd.to_numeric(df['DLC'], errors='coerce').fillna(0).astype(int)
    
    if attack_label == 0:
        df['Label'] = 0
    else:
        df['Label'] = df['Flag'].apply(lambda x: attack_label if x.strip() == 'T' else 0)
        
    print(f"Original class balance for {os.path.basename(filepath)}:")
    print(df['Label'].value_counts())
    
    if len(df) > sample_size:
        frac = sample_size / len(df)
        df = df.groupby('Label', group_keys=False).apply(lambda x: x.sample(frac=frac, random_state=42))
        
    print(f"Sampled class balance for {os.path.basename(filepath)}:")
    print(df['Label'].value_counts())
    
    return df

def main():
    all_dfs = []
    
    for filename, attack_label in DATASETS.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"WARNING: File {filepath} not found!")
            continue
            
        df = process_and_sample_file(filepath, attack_label)
        all_dfs.append(df)
        
    if not all_dfs:
        print("No data found!")
        return
        
    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df = full_df.sort_values(by='Timestamp').reset_index(drop=True)
    
    print("\nFinal combined class balance:")
    print(full_df['Label'].value_counts())
    print("\nTotal rows:", len(full_df))
    print("\nSample rows:")
    print(full_df.sample(5, random_state=42))
    
    full_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved combined dataset to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
