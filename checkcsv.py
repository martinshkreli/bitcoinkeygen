import csv
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_row_in_privatekey(privatekey_filename, value):
    with open(privatekey_filename, 'r') as privatekey_file:
        privatekey_reader = csv.reader(privatekey_file)
        for row in privatekey_reader:
            if int(row[0]) == value:
                return row
    return None

def get_rows_for_range(privatekey_filename, start, end):
    rows = []
    with open(privatekey_filename, 'r') as privatekey_file:
        privatekey_reader = csv.reader(privatekey_file)
        for row in privatekey_reader:
            val = int(row[0])
            if start <= val <= end:
                rows.append(row)
    return rows

def process_and_fix_csv(original_filename, privatekey_filename):
    prev_value = -1
    row_number = 0
    inconsistencies_fixed = 0
    
    with open(original_filename, 'r') as csv_file, open("temp.csv", 'w', newline='') as temp_file:
        csv_reader = csv.reader(csv_file)
        csv_writer = csv.writer(temp_file)

        logging.info("Starting to check and fix CSV file for missing data...")
        for row in csv_reader:
            try:
                current_value = int(row[0])
                if current_value != prev_value + 1:
                    missing_start = prev_value + 1
                    missing_end = current_value - 1

                    # Fetch rows for missing range
                    missing_rows = get_rows_for_range(privatekey_filename, missing_start, missing_end)

                    if missing_rows:
                        csv_writer.writerows(missing_rows)
                        inconsistencies_fixed += len(missing_rows)
                        logging.info(f"Fixed inconsistency for range {missing_start}-{missing_end}.")
                    else:
                        logging.warning(f"Data for expected range {missing_start}-{missing_end} not found in privatekey.csv.")
                
                csv_writer.writerow(row)
                prev_value = current_value
                row_number += 1
                
                if row_number % 10_000_000 == 0:
                    logging.info(f"Processed {row_number} rows so far.")
            except ValueError:
                logging.error(f"Row {row_number}: Value in the first column is not a valid integer.")
                csv_writer.writerow(row)
                row_number += 1

    os.remove(original_filename)
    os.rename("temp.csv", original_filename)

    logging.info(f"Finished processing. Total rows: {row_number}. Rows added: {inconsistencies_fixed}.")

def main():
    original_filename = "oneBillion.csv"
    privatekey_filename = "xaa.csv"
    
    process_and_fix_csv(original_filename, privatekey_filename)
    print("Finished processing and fixing the CSV file.")

if __name__ == "__main__":
    main()
