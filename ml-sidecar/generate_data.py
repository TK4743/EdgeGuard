import csv
import os
import random


def generate_can_message(timestamp, attack_type=None):
    can_id = f"{random.randint(0, 2047):04x}"
    dlc = 8
    data = [f"{random.randint(0, 255):02x}" for _ in range(8)]
    flag = 'R'

    if attack_type == 'DoS':
        can_id = '0000'
        data = ['00'] * 8
        flag = 'T'
    elif attack_type == 'Fuzzy':
        can_id = f"{random.randint(0, 2047):04x}"
        data = [f"{random.randint(0, 255):02x}" for _ in range(8)]
        flag = 'T'
    elif attack_type == 'Spoofing':
        can_id = '043f' # Gear message
        data[0] = 'ff'
        flag = 'T'

    return [f"{timestamp:.6f}", can_id.upper(), dlc] + [d.upper() for d in data] + [flag]

def create_dataset(filename, num_rows, attack_type=None, attack_ratio=0.1):
    filepath = os.path.join('../data', filename)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        current_time = 1478198376.0
        for _ in range(num_rows):
            current_time += random.uniform(0.0001, 0.001)
            is_attack = random.random() < attack_ratio if attack_type else False
            msg = generate_can_message(current_time, attack_type if is_attack else None)
            writer.writerow(msg)
    print(f"Generated {filepath} with {num_rows} rows.")

if __name__ == '__main__':
    os.makedirs('../data', exist_ok=True)
    # Generate synthetic datasets (reduced size for quick testing)
    create_dataset('normal_run_data.txt', 10000)
    create_dataset('DoS_dataset.csv', 10000, 'DoS', 0.15)
    create_dataset('Fuzzy_dataset.csv', 10000, 'Fuzzy', 0.15)
    create_dataset('spoofing_gear_dataset.csv', 10000, 'Spoofing', 0.15)
