import csv

input_file = "0-1413000000.csv"
output_file = "1413000000.csv"

# Initialize the expected integer
expected_next = 0

with open(input_file, mode='r', newline='') as infile, open(output_file, mode='w', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        try:
            current_value = int(row[0])
            if current_value == expected_next:
                writer.writerow(row)
                expected_next += 1
            # Else, it's an out-of-sequence value, skip writing it to the output
        except ValueError:
            # Handle potential non-integer values gracefully
            print(f"Encountered a non-integer value {row[0]}. Skipping...")

input("Press Enter to continue...")
filename = "1413000000.csv"

with open(filename, 'r') as f:
    line_count = sum(1 for line in f)

print(f"The file {filename} has {line_count} lines.")
