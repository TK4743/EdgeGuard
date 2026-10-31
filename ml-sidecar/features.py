from collections import defaultdict, deque

import numpy as np


def compute_payload_entropy(payloads):
    """
    Compute Shannon entropy for an array of payloads.
    payloads: N x 8 numpy array of integers.
    Vectorized for speed.
    """
    # Create an array of shape (N, 256) where each row is a count of bytes
    # To do this efficiently, we can use np.apply_along_axis or a fast loop.
    # Since N can be 300,000, we'll use a fast custom implementation.
    N = payloads.shape[0]
    entropy_vals = np.zeros(N, dtype=np.float32)
    
    # We can compute entropy quickly in python loop since it's just 8 elements per row,
    # but let's try a more vectorized approach if possible.
    # Actually, a simple loop with numba would be fastest, but without numba:
    
    for i in range(N):
        row = payloads[i]
        # fast unique counts
        _, counts = np.unique(row, return_counts=True)
        p = counts / 8.0
        entropy_vals[i] = -np.sum(p * np.log2(p))
        
    return entropy_vals

def extract_features(df):
    """
    Extracts features for the ML model.
    Must match Java FeatureExtractor exactly!
    """
    df = df.copy()
    
    print("Extracting CAN_ID_INT...")
    df['CAN_ID_INT'] = df['CAN_ID'].apply(lambda x: int(str(x), 16)).astype(np.float32)
    
    print("Extracting DLC...")
    df['DLC'] = df['DLC'].astype(np.float32)
    
    print("Extracting Time_Delta...")
    # Time delta since last message of SAME CAN_ID
    # Must ensure dataframe is sorted by Timestamp overall, but groupby diff operates on group level.
    # To be perfectly correct with time ordering, we should ensure the data is sorted by timestamp first.
    # load_data.py already sorts by timestamp.
    df['Time_Delta'] = df.groupby('CAN_ID')['Timestamp'].diff().fillna(0).astype(np.float32)
    
    print("Extracting Payload Features...")
    data_cols = ['DATA0', 'DATA1', 'DATA2', 'DATA3', 'DATA4', 'DATA5', 'DATA6', 'DATA7']
    for col in data_cols:
        df[col] = df[col].apply(lambda x: int(str(x), 16))
        
    payloads = df[data_cols].values
    
    # 4. Payload Entropy
    df['Payload_Entropy'] = compute_payload_entropy(payloads)
    
    # 5. Byte Variance
    # ddof=0 matches np.var and Java's calculation.
    df['Byte_Variance'] = np.var(payloads, axis=1, ddof=0).astype(np.float32)
    
    # 6. Hamming Weight
    def hamming_weight(row):
        return sum(val.bit_count() for val in row)
    
    df['Hamming_Weight'] = np.apply_along_axis(hamming_weight, 1, payloads).astype(np.float32)
    
    print("Extracting Temporal Features...")
    can_ids = df['CAN_ID'].values
    time_deltas = df['Time_Delta'].values
    
    N = len(can_ids)
    freq_50 = np.zeros(N, dtype=np.float32)
    inter_arrival_var = np.zeros(N, dtype=np.float32)
    
    # Efficient rolling window (sliding window of 50 for global messages)
    window = deque()
    counts_dict = {}
    
    # Inter arrival variance history
    id_delta_history = defaultdict(lambda: deque(maxlen=5))
    
    for i in range(N):
        cid = can_ids[i]
        delta = time_deltas[i]
        
        # 7. ID Freq 50
        window.append(cid)
        counts_dict[cid] = counts_dict.get(cid, 0) + 1
        if len(window) > 50:
            removed = window.popleft()
            counts_dict[removed] -= 1
        freq_50[i] = counts_dict[cid]
        
        # 8. Inter Arrival Variance
        hist = id_delta_history[cid]
        hist.append(delta)
        if len(hist) > 1:
            # np.var defaults to ddof=0, which matches Java's sum(diff^2)/N
            inter_arrival_var[i] = np.var(hist)
        else:
            inter_arrival_var[i] = 0.0
            
    df['ID_Freq_50'] = freq_50
    df['Inter_Arrival_Var'] = inter_arrival_var
    
    return df

def apply_top_ids(df, top_ids):
    for top_id in top_ids:
        df[f'Is_{top_id}'] = (df['CAN_ID'] == top_id).astype(np.float32)
        
    top_id_cols = [f'Is_{top_id}' for top_id in top_ids]
    feature_cols = [
        'CAN_ID_INT', 'DLC', 'Time_Delta', 
        'Payload_Entropy', 'Byte_Variance', 'Hamming_Weight',
        'ID_Freq_50', 'Inter_Arrival_Var'
    ] + top_id_cols
    
    labels = df['Label'] if 'Label' in df.columns else None
    return df[feature_cols].astype(np.float32), labels
