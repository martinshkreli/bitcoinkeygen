from list_data import addlist
import logging
import argparse
from concurrent.futures import ProcessPoolExecutor
import time
addlist_set = set(addlist)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#y^2 = x^3 + 7
p =  18674555287607
order = 18674555287607
genX = 6114398
genY = 7432090106596

def mmi(x,p):
    return pow(x,-1,p)

def doublepoint(x,y):
    slope=((3*x**2) * mmi(2*y,p))%p
    newx=(slope**2 - 2*x)%p
    newy=((slope*(x - newx)) - y)%p
    return newx,newy

def addpoint(x,y,a,b):
  if(x==a and y==b):
    return doublepoint(x,y) # double check this
  slope=((y-b) * mmi(x-a, p))%p
  returnx = (((slope**2) - x - a)%p)
  returny = (slope* (x - returnx)- y)%p
  return returnx,returny

def multiplypoint(k, genX, genY):
    resultX, resultY = 0, 0
    currentX, currentY = genX, genY
    while k > 0:
        print(k)
        if k & 1:
            if resultX == 0 and resultY == 0:
                resultX, resultY = currentX, currentY
            else:
                resultX, resultY = addpoint(resultX, resultY, currentX, currentY)
        currentX, currentY = doublepoint(currentX, currentY)
        k >>= 1
    return resultX, resultY

def generate(privatekeydecimal):
    pubkeyx, pubkeyy = multiplypoint(privatekeydecimal, genX, genY)
    return [privatekeydecimal, pubkeyx, pubkeyy]

def chunked_range(start, end, chunk_size):
    for i in range(start, end, chunk_size):
        yield (i, min(i + chunk_size, end))

def process_chunk(range_tuple):
    start, end = range_tuple
    try:
        #logging.info(f"Starting processing for range {start} to {end}")
        generated_keys = [generate(i) for i in range(start, end)]
        #logging.info(f"Completed processing for range {start} to {end}")
        return generated_keys
    except Exception as e:
        logging.error(f"Error processing range {start} to {end}: {e}")
        return f"Error processing range {start} to {end}: {e}"

def main():
    parser = argparse.ArgumentParser(description="Generate Bitcoin addresses and check them against a list.")
    parser.add_argument("--start", type=int, default=0, help="Starting value for key generation.")
    parser.add_argument("--end", type=int, default=10000000000, help="Ending value for key generation.")
    args = parser.parse_args()

    start_val = args.start
    end_val = args.start + 100000
    chunk_size = 100000 // 22
    num_workers = 20

    while start_val < end_val:
        logging.info(f"Generating keys from {start_val} to {end_val}")
        start_time = time.time()
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(process_chunk, chunked_range(start_val, end_val, chunk_size)))
        elapsed_time = time.time() - start_time

        all_keys = []
        for (generated_keys) in results:
            all_keys.extend(generated_keys)
        
        throughput = len(all_keys) / elapsed_time
        logging.info(f"Throughput: {throughput:.2f} keys/sec")

        with open('integers_smaller.csv', 'a') as f:
            for key in all_keys:
                f.write(f"{key[0]},{key[1]}\n")
                
        start_val = end_val
        end_val += 100000

if __name__ == "__main__":
    main()