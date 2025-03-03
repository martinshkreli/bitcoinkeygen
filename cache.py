from large_wallets import largest   #external dictionary
import logging
from hashlib import sha256  #python standard library
from Crypto.Hash import RIPEMD  #pycryptodome
import base58   #external   
import json
import os
import atexit
import time

# Configuration
MAX_KEYS = 150000  # Maximum number of keys to generate
CACHE_FILE = 'point_cache.json'
CACHE_SAVE_INTERVAL = 1000  # How often to show cache progress
KEY_PROGRESS_INTERVAL = 100  # How often to show key generation progress
MAINNET_PRIVATE_KEY_PREFIX = "80"  # Version byte for mainnet private keys
MAINNET_PUBLIC_KEY_PREFIX = "00"   # Version byte for mainnet addresses

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Bitcoin elliptic curve parameters (secp256k1)
p = 2 ** 256 - 2 ** 32 - 2 ** 9 - 2 ** 8 - 2 ** 7 - 2 ** 6 - 2 ** 4 - 1  # Prime field
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240  # Generator point X
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424  # Generator point Y

# Initialize cache
cache = {}
cache_modified = False
addlist_set = set(largest)

def save_cache_on_exit():
    if cache_modified:
        save_cache()

atexit.register(save_cache_on_exit)

def save_cache():
    serializable_cache = {}
    for path, point in cache.items():
        serializable_cache[path] = [str(point[0]), str(point[1])]
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(serializable_cache, f)
    global cache_modified
    cache_modified = False

def load_cache():
    global cache
    cache = {}
    
    if not os.path.exists(CACHE_FILE):
        print("No cache file found. Starting with empty cache.")
        return
        
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            
            # Check if it's old format (list) or new format (dict)
            if isinstance(data, list):
                print("Converting old format cache to new format...")
                os.remove(CACHE_FILE)  # Remove old format file
                return
            
            # New format
            for path, point in data.items():
                cache[path] = (int(point[0]), int(point[1]))
                
        print(f"Loaded {len(cache)} cached points")
    except (json.JSONDecodeError, IOError, ValueError) as e:
        print(f"Error loading cache: {e}. Starting fresh.")
        cache = {}
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

def mmi(x,p):
    return pow(x,-1,p)

def doublepoint(x,y):
    slope = ((3*x**2) * mmi(2*y,p))%p
    newx = (slope**2 - 2*x)%p
    newy = ((slope*(x - newx)) - y)%p
    return newx, newy

def addpoint(x,y,a,b):
    if x==a and y==b:
        return doublepoint(x,y)
    
    slope = ((y-b) * mmi(x-a, p))%p
    returnx = (((slope**2) - x - a)%p)
    returny = (slope*(x - returnx)- y)%p
    return returnx, returny

def build_cache_tree(max_number):
    global cache_modified
    
    # Start with generator point
    if '' not in cache:
        cache[''] = (genX, genY)
        cache_modified = True
    
    # Get binary representation of max number to determine needed paths
    binary_max = bin(max_number)[2:]  # Remove '0b' prefix
    max_depth = len(binary_max)
    print(f"Building cache tree to depth {max_depth} for paths needed up to {max_number}")
    
    # Build paths incrementally
    for i in range(max_number + 1):
        binary = bin(i)[3:]  # Skip first '0b1'
        if not binary:  # Handle special case for 0
            continue
            
        if binary not in cache:
            # Calculate point for this path
            current_point = cache['']  # Start with generator point
            for bit in binary:
                # Always double
                current_point = doublepoint(current_point[0], current_point[1])
                # Add if bit is 1
                if bit == '1':
                    current_point = addpoint(current_point[0], current_point[1], genX, genY)
            cache[binary] = current_point
            cache_modified = True
            
            if len(cache) % CACHE_SAVE_INTERVAL == 0:
                print(f"Cached {len(cache)} points...")
                save_cache()  # Save periodically to avoid data loss
    
    print(f"Completed cache with {len(cache)} points")
    save_cache()  # Final save

def multiplypoint(k, genX, genY):
    binarypoint = bin(k)[2:]
    
    # Build cache if needed for this number
    if len(cache) == 0:
        print("Building initial cache...")
        build_cache_tree(MAX_KEYS)  # Build complete cache for our range
    
    # Use the cached path
    path = binarypoint[1:]  # Skip first 1
    if path not in cache:
        print(f"Path {path} not found in cache! Rebuilding cache...")
        build_cache_tree(MAX_KEYS)
        if path not in cache:
            raise ValueError(f"Failed to generate path {path} for number {k}")
    
    return cache[path]

def generate(privatekeydecimal):
    pubkeyx, pubkeyy = multiplypoint(privatekeydecimal, genX, genY)
    
    # Format private key - start with version byte
    hex_private_key = hex(privatekeydecimal)[2:].zfill(64)
    versioned_private_key = MAINNET_PRIVATE_KEY_PREFIX + hex_private_key
    
    # First SHA256
    first_sha256 = sha256(bytes.fromhex(versioned_private_key)).digest()
    # Second SHA256
    second_sha256 = sha256(first_sha256).digest()
    # Get checksum (first 4 bytes)
    checksum = second_sha256[:4].hex()
    
    # Combine version + private key + checksum
    final_key = versioned_private_key + checksum
    
    # Convert to WIF using base58
    privatekeyWIF = base58.b58encode(bytes.fromhex(final_key))
    
    # Format public key
    appendcode = "03" if int(hex(pubkeyy)[-1], 16) % 2 else "02"
    publickeyhex = appendcode + hex(pubkeyx)[2:].zfill(64)
    
    # 3. Compute the Bitcoin address from the public key
    sha256_hash = sha256(bytes.fromhex(publickeyhex)).digest()
    ripemd160_hash = RIPEMD.new(sha256_hash).digest()
    version_ripemd160_hash = bytes.fromhex(MAINNET_PUBLIC_KEY_PREFIX) + ripemd160_hash
    
    # Double SHA256 for checksum
    double_sha256 = sha256(sha256(version_ripemd160_hash).digest()).digest()
    checksum = double_sha256[:4]
    
    # Combine version + hash + checksum
    binary_address = version_ripemd160_hash + checksum
    
    # Convert to base58
    address = base58.b58encode(binary_address)
    
    return [privatekeydecimal, versioned_private_key, privatekeyWIF, pubkeyx, publickeyhex, binary_address.hex(), address]

def print_key_details(key_data):
    #print("\nPrivate Key Details:")
    #print(f"Integer: {key_data[0]}")
    #print(f"Hex    : {key_data[1]}")
    #print(f"WIF    : {key_data[2].decode()}")
    #print("\nPublic Key Details:")
    #print(f"X Coordinate: {key_data[3]}")
    #print(f"Compressed Hex: {key_data[4]}")
    #print(f"Bitcoin Address: {key_data[6].decode()}")
    print("-" * 80)

def main():
    print("Loading cache...")
    load_cache()
    print(f"Generating first {MAX_KEYS} Bitcoin key pairs...")
    print("=" * 80)
    
    start_time = time.time()
    for i in range(0, MAX_KEYS):
        key_data = generate(i)
        if (i + 1) % KEY_PROGRESS_INTERVAL == 0:
            elapsed = time.time() - start_time
            keys_per_second = (i + 1) / elapsed
            print(f"Generated {i + 1} keys... ({keys_per_second:.2f} keys/sec)")

if __name__ == "__main__":
    main()