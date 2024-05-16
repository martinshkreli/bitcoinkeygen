from list_data import addlist
import logging
import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from Crypto.Hash import RIPEMD
import base58
import time
addlist_set = set(addlist)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#y^2 = x^3 + 7
p =  2 ** 256 - 2 ** 32 - 2 ** 9 - 2 ** 8 - 2 ** 7 - 2 ** 6 - 2 ** 4 - 1
#        115792089237316195423570985008687907853269984665640564039457584007908834671663 # p
order =  115792089237316195423570985008687907852837564279074904382605163141518161494337 # n, supposed to be less than P, 78 DIGITS;
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424

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
    currentGenX = genX
    currentGenY = genY
    
    binarypoint = (bin(k)[3:]) #the number 3 is used to remove 0b (2 characters) and the first binary character (1 character)
    
    for y in binarypoint:
        currentGenX, currentGenY = doublepoint(currentGenX,currentGenY)
        if(y=='1'): 
            currentGenX, currentGenY = addpoint(currentGenX, currentGenY, genX, genY)
    return currentGenX, currentGenY

def generate(privatekeydecimal):
    # 1. Compute the public key from the private key using elliptic curve operations
    pubkeyx, pubkeyy = multiplypoint(privatekeydecimal, genX, genY)
    privatekeyhex = "80" + hex(privatekeydecimal)[2:].rjust(64, '0')
    
    appendcode = "03" if int(hex(pubkeyy)[-1], 16) % 2 else "02"
    publickeyhex = appendcode + hex(pubkeyx)[2:].rjust(64, '0')
    
    # 2. Compute the Wallet Import Format (WIF) for the private key
    firsthashedprivatekey = sha256(bytes.fromhex(privatekeyhex)).hexdigest()
    fourBytes = sha256(bytes.fromhex(firsthashedprivatekey)).hexdigest()[:8]
    finalprivatekey = (privatekeyhex + fourBytes).upper()
    
    # Use the inbuilt base58 encoding function with checksum for WIF
    privatekeyWIF = base58.b58encode_check(bytes.fromhex(finalprivatekey))
    
    # 3. Compute the Bitcoin address from the public key
    postSHApublickey = sha256(bytes.fromhex(publickeyhex)).digest()
    hashed_data = RIPEMD.new(postSHApublickey).digest()
    postRIPEMDpublickey = "00" + hashed_data.hex()
    preFinalHashobjectDecoded = sha256(bytes.fromhex(postRIPEMDpublickey)).hexdigest()
    pubFourBytes = sha256(bytes.fromhex(preFinalHashobjectDecoded)).hexdigest()[:8]
    finalpublickeyHex = (postRIPEMDpublickey + pubFourBytes).upper()

    # Use the inbuilt base58 encoding function with checksum for Bitcoin address
    finalpublickeyB58 = base58.b58encode_check(bytes.fromhex(finalpublickeyHex))
    
    return [privatekeydecimal, privatekeyhex, privatekeyWIF, pubkeyx, publickeyhex, finalpublickeyHex, finalpublickeyB58]

def chunked_range(start, end, chunk_size):
    """Yield successive chunk_size-sized chunks from start to end."""
    for i in range(start, end, chunk_size):
        yield (i, min(i + chunk_size, end))

def process_chunk(range_tuple):
    start, end = range_tuple
    try:
        #logging.info(f"Starting processing for range {start} to {end}")
        generated_keys = [generate(i) for i in range(start, end)]
        found_keys = [key for key in generated_keys if key[6] in addlist_set]
        #logging.info(f"Completed processing for range {start} to {end}")
        return (generated_keys, found_keys)
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
        for (generated_keys, found_keys) in results:
            all_keys.extend(generated_keys)
            if found_keys:
                for key in found_keys:
                    print(key)
                    print('FOUND ONE!')
        
        throughput = len(all_keys) / elapsed_time
        logging.info(f"Throughput: {throughput:.2f} keys/sec")

        with open('integers.csv', 'a') as f:
            for key in all_keys:
                f.write(f"{key[0]},{key[3]}\n")
                #f.write(f"{key[0]},{key[3]},{str(key[6])[2:-1]}\n")
                
        start_val = end_val
        end_val += 100000

if __name__ == "__main__":
    main()