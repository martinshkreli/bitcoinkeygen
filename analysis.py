import csv
import numpy as np

file_path = 'integers.csv'

def calculate_chunk_statistics(file_path, chunk_size=5000000):
    total_count = 0
    total_sum = 0
    total_squares_sum = 0
    global_min = float('inf')
    global_max = float('-inf')

    with open(file_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')

        while True:
            chunk = [int(row[1]) for _, row in zip(range(chunk_size), csvreader)]
            if not chunk:
                break
            
            total_count += len(chunk)
            total_sum += sum(chunk)
            total_squares_sum += sum(x**2 for x in chunk)
            global_min = min(global_min, min(chunk))
            global_max = max(global_max, max(chunk))
            chunk_average = sum(chunk) / len(chunk)
            print('\nTotal Count:', total_count)
            print(f"Chunk Avg : {chunk_average:.0f}")
            print('Global Min:', global_min, len(str(global_min)))
            print('Global Max:', global_max, len(str(global_max)))
            global_average = total_sum / total_count
            print('Global Average:', global_average, len(str(global_average)))
            print('')
                  
    overall_average = total_sum / total_count
    variance = (total_squares_sum / total_count) - (overall_average ** 2)
    std_dev = variance ** 0.5

    return overall_average, global_min, global_max, std_dev

avg, min_val, max_val, std_dev = calculate_chunk_statistics(file_path)

print(f"\nOverall Average: {avg:.0f}")
print(f"Standard Deviation: {std_dev:.0f}")
print(f"Minimum: {min_val}")
print(f"Maximum: {max_val}")
