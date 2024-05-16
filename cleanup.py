import csv

input_file = "0-1413000000.csv"
output_file = "1413000000.csv"
expected_next = 0

with open(input_file, mode='r', newline='') as infile, open(output_file, mode='w', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        try:
            current_value = int(row[0])
            while current_value > expected_next:
                expected_next += 1
            if current_value == expected_next:
                writer.writerow(row)
                expected_next += 1
        except ValueError:
            print(f"Encountered a non-integer value {row[0]}. Skipping...")

input("Press Enter to continue...")

with open(output_file, 'r') as f:
    line_count = sum(1 for line in f)

print(f"The file {output_file} has {line_count} lines.")
