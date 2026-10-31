import json
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd


def test():
    columns = ['Timestamp', 'CAN_ID', 'DLC', 'DATA0', 'DATA1', 'DATA2', 'DATA3', 'DATA4', 'DATA5', 'DATA6', 'DATA7', 'Flag']
    data = [
        ["1478198376.389427", "0316", "8", "05", "21", "68", "09", "21", "21", "00", "6f", "R"],
        ["1478198376.389636", "018f", "8", "fe", "5b", "00", "00", "00", "3c", "00", "00", "R"]
    ]
    df = pd.DataFrame(data, columns=columns)
    
    df['CAN_ID_INT'] = df['CAN_ID'].apply(lambda x: int(str(x), 16))
    df['Timestamp'] = df['Timestamp'].astype(float)
    df = df.sort_values(by=['CAN_ID', 'Timestamp'])
    df['Time_Delta'] = df.groupby('CAN_ID')['Timestamp'].diff().fillna(0).astype(np.float32)
    df = df.sort_values(by='Timestamp')
    
    data_cols = ['DATA0', 'DATA1', 'DATA2', 'DATA3', 'DATA4', 'DATA5', 'DATA6', 'DATA7']
    for col in data_cols:
        df[col] = df[col].apply(lambda x: int(str(x), 16))
        
    payloads = df[data_cols].values
    
    entropy_vals = np.zeros(len(payloads), dtype=np.float32)
    byte_var = np.var(payloads, axis=1).astype(np.float32)
    hamming_weights = np.zeros(len(payloads), dtype=np.float32)
    
    for i in range(len(payloads)):
        row = payloads[i]
        _, counts = np.unique(row, return_counts=True)
        p = counts / 8.0
        entropy_vals[i] = -np.sum(p * np.log2(p))
        hamming_weights[i] = sum(int(val).bit_count() for val in row)
        
    df['Payload_Entropy'] = entropy_vals
    df['Byte_Variance'] = byte_var
    df['Hamming_Weight'] = hamming_weights
    
    can_ids = df['CAN_ID_INT'].values
    time_deltas = df['Time_Delta'].values
    
    freq_50 = np.zeros(len(can_ids), dtype=np.float32)
    inter_arrival_var = np.zeros(len(can_ids), dtype=np.float32)
    
    window = deque()
    counts_dict = {}
    id_delta_history = defaultdict(lambda: deque(maxlen=5))
    
    for i in range(len(can_ids)):
        cid = can_ids[i]
        delta = time_deltas[i]
        
        window.append(cid)
        counts_dict[cid] = counts_dict.get(cid, 0) + 1
        if len(window) > 50:
            removed = window.popleft()
            counts_dict[removed] -= 1
        freq_50[i] = counts_dict[cid]
        
        hist = id_delta_history[cid]
        hist.append(delta)
        if len(hist) > 1:
            inter_arrival_var[i] = np.var(hist)
        else:
            inter_arrival_var[i] = 0.0
            
    df['ID_Freq_50'] = freq_50
    df['Inter_Arrival_Var'] = inter_arrival_var
    
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_config.json')
    try:
        with open(config_path, 'r') as f:
            top_ids = json.load(f)['top_5_can_ids']
    except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError):
        top_ids = ["043F", "0000", "0482", "04DD", "04A1"]
        
    for top_id in top_ids:
        df[f'Is_{top_id}'] = (df['CAN_ID'] == top_id).astype(np.float32)
        
    top_id_cols = [f'Is_{top_id}' for top_id in top_ids]
    feature_cols = ['CAN_ID_INT', 'DLC', 'Time_Delta', 'Payload_Entropy', 'Byte_Variance', 'Hamming_Weight', 'ID_Freq_50', 'Inter_Arrival_Var'] + top_id_cols
    
    X = df[feature_cols].astype(np.float32)
    
    for idx, row in X.iterrows():
        print(f"Message {idx + 1} Python features: {list(row.values)}")

if __name__ == '__main__':
    test()
