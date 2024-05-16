import csv

input_file_path = 'integers.csv'
output_file_path = 'integerstrunc.csv'

def modify_csv(input_file, output_file):
    with open(input_file, 'r', newline='') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for row in reader:
            if len(row) >= 2 and row[1].isdigit():
                modified_integer = row[1][:-65] if len(row[1]) > 65 else row[1]
                writer.writerow([row[0], modified_integer])

modify_csv(input_file_path, output_file_path)
