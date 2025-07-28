import logging
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256, new as hash_new
import time
import secrets
from multiprocessing import Manager
import traceback

try:
    from coincurve import PrivateKey
    COINCURVE_AVAILABLE = True
except ImportError:
    COINCURVE_AVAILABLE = False

# --- secp256k1 curve constants ---
p = 2**256 - 2**32 - 2**9 - 2**8 - 2**7 - 2**6 - 2**4 - 1
n = 115792089237316195423570985008687907852837564279074904382605163141518161494337
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424

# --- Encoding constants ---
CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# --- Bech32 Encoding ---
def _bech32_polymod(vals):
    g = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in vals:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= g[i]
    return chk

def _hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def _convert_bits(data, from_bits, to_bits, pad=True):
    acc = 0; bits = 0; ret = []
    maxv = (1 << to_bits) - 1
    for b in data:
        acc = (acc << from_bits) | b
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (to_bits - bits)) & maxv)
    return ret

def bech32_encode(hrp, witver, witprog):
    data = [witver] + _convert_bits(witprog, 8, 5)
    values = _hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + '1' + ''.join(CHARSET[d] for d in data + checksum)

# --- Base58 Encoding ---
def base58_encode(b: bytes) -> str:
    n_val = int.from_bytes(b, 'big')
    s = []
    while n_val > 0:
        n_val, r = divmod(n_val, 58)
        s.append(ALPHABET[r])
    s = ''.join(reversed(s))
    leading_zeros = len(b) - len(b.lstrip(b'\x00'))
    return '1' * leading_zeros + s

def base58_check_encode(prefix: bytes, payload: bytes) -> str:
    data = prefix + payload
    sha1 = sha256(data).digest()
    sha2 = sha256(sha1).digest()
    checksum = sha2[:4]
    full = data + checksum
    return base58_encode(full)

# --- Elliptic Curve Cryptography ---
def mmi(x, p_val=p):
    return pow(x, -1, p_val)

def doublepoint(x, y):
    slope = (3 * x * x * mmi(2 * y)) % p
    newx = (slope * slope - 2 * x) % p
    newy = (slope * (x - newx) - y) % p
    return newx, newy

def addpoint(x1, y1, x2, y2):
    if x1 == x2 and y1 == y2:
        return doublepoint(x1, y1)
    slope = ((y1 - y2) * mmi(x1 - x2)) % p
    newx = (slope * slope - x1 - x2) % p
    newy = (slope * (x1 - newx) - y1) % p
    return newx, newy

def multiplypoint_slow(k, gx=genX, gy=genY):
    """Pure-python, non-constant-time scalar multiplication. For educational use."""
    if not (1 <= k < n):
        raise ValueError(f"Private key {k} is not in the valid range [1, n-1]")
    x, y = gx, gy
    for bit in bin(k)[3:]:
        x, y = doublepoint(x, y)
        if bit == '1':
            x, y = addpoint(x, y, gx, gy)
    return x, y

def multiplypoint_fast(k, gx=None, gy=None):
    """High-speed scalar multiplication using coincurve (libsecp256k1)."""
    # coincurve's from_int handles the range check
    pk_obj = PrivateKey.from_int(k)
    pub_point = pk_obj.public_key.point()
    x = int.from_bytes(pub_point[:32], 'big')
    y = int.from_bytes(pub_point[32:], 'big')
    return x, y

# --- Address Generation ---
def pubkey_to_addresses(pubkey_hex):
    pk = bytes.fromhex(pubkey_hex)
    h160 = hash_new('ripemd160', sha256(pk).digest()).digest()
    p2pkh = base58_check_encode(b'\x00', h160)
    redeem = b'\x00\x14' + h160
    h160_r = hash_new('ripemd160', sha256(redeem).digest()).digest()
    p2sh_p2w = base58_check_encode(b'\x05', h160_r)
    bech = bech32_encode('bc', 0, h160)
    return p2pkh, p2sh_p2w, bech

def generate_key_material(privatekeydecimal, ec_multiply_func):
    pubx, puby = ec_multiply_func(privatekeydecimal)
    priv_bytes = privatekeydecimal.to_bytes(32, 'big')
    wif = base58_check_encode(b'\x80', priv_bytes + b'\x01')
    prefix = b'\x02' if (puby & 1) == 0 else b'\x03'
    pubkey_bytes = prefix + pubx.to_bytes(32, 'big')
    sha_digest = sha256(pubkey_bytes).digest()
    ripe = hash_new('ripemd160', sha_digest).digest()
    addr = base58_check_encode(b'\x00', ripe)
    return privatekeydecimal, pubx, puby, addr, wif, pubkey_bytes.hex()

# --- Parallel Processing ---
def process_chunk(args):
    chunk_start, chunk_end, gen_func, output_y = args
    out = []
    for i in range(chunk_start, chunk_end):
        try:
            priv, pubx, puby, addr, _, _ = generate_key_material(i, gen_func)
            if output_y:
                out.append(f"{priv},{pubx},{puby},{addr}\n")
            else:
                out.append(f"{priv},{pubx},{addr}\n")
        except Exception:
            logging.error(f"Failed to process key {i}:\n{traceback.format_exc()}")
    return "".join(out)

def process_range_parallel(start, end, output, workers, chunk_size, gen_func, include_y):
    total = end - start
    # Create chunks as tuples of (start, end, func, include_y)
    chunks = [(i, min(i + chunk_size, end), gen_func, include_y) for i in range(start, end, chunk_size)]
    t0 = time.time()
    
    # Use a manager for the lock for cross-platform compatibility
    manager = Manager()
    lock = manager.Lock()
    
    try:
        with open(output, 'x') as f:
            header = "private_key,public_key_x,public_key_y,address\n" if include_y else "private_key,public_key_x,address\n"
            f.write(header)
    except FileExistsError:
        pass
        
    with ProcessPoolExecutor(max_workers=workers) as exe, open(output, 'a', buffering=1<<20) as f:
        futures = {exe.submit(process_chunk, c): c[1]-c[0] for c in chunks}
        done = 0
        for fut in as_completed(futures):
            chunk_data = fut.result()
            with lock:
                f.write(chunk_data)
            
            done += futures[fut]
            logging.info(f"Progress: {done}/{total} ({done/total:.2%})")
            
    elapsed = time.time() - t0
    rate = total / elapsed if elapsed > 0 else 0
    print(f"\nCompleted {total} keys in {elapsed:.2f}s => {rate:.2f} keys/sec")

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(
        description="High-speed Bitcoin key generator. Requires 'coincurve'.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--privatekey", type=int, help="Generate keys for a single private key.")
    group.add_argument("--random", action="store_true", help="Generate a single random private key.")
    group.add_argument("--pubkey", type=str, help="Derive addresses from a compressed public key hex.")
    group.add_argument("--start", type=int, help="Start of the private key range. Requires --end.")

    parser.add_argument("--end", type=int, help="End of the private key range (exclusive).")
    parser.add_argument("--output", type=str, default="output.csv")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=10000)
    parser.add_argument("--no-y", action="store_true", help="Don't include the Y coordinate in output.")
    parser.add_argument("--fast", action="store_true", default=True, help="Use fast C-backend (coincurve). Default is true.")
    parser.add_argument("--slow", action="store_false", dest='fast', help="Use slow pure-python implementation.")

    args = parser.parse_args()
    
    if (genY * genY) % p != (genX * genX * genX + 7) % p:
        logging.critical("FATAL: Generator point is not on the secp256k1 curve.")
        return

    # Select the multiplication function
    if args.fast:
        if not COINCURVE_AVAILABLE:
            logging.critical("FATAL: --fast mode requires 'coincurve'. Please run 'pip install coincurve'.")
            return
        ec_multiply_func = multiplypoint_fast
    else:
        ec_multiply_func = multiplypoint_slow

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    def print_key_details(priv, pubx, puby, wif, compressed_hex):
        p2pkh, p2sh_p2w, bech = pubkey_to_addresses(compressed_hex)
        print(f"Private Key (Decimal): {priv}\nPrivate Key (WIF Comp): {wif}\n" + "-"*25)
        print(f"Public Key X: {pubx}\nPublic Key Y: {puby}\nPublic Key (Compressed): {compressed_hex}\n" + "-"*25)
        print(f"Address (P2PKH/Legacy):   {p2pkh}\nAddress (P2SH-P2WPKH):    {p2sh_p2w}\nAddress (P2WPKH/Bech32):  {bech}")

    if args.privatekey is not None:
        try:
            _, pubx, puby, _, wif, comp = generate_key_material(args.privatekey, ec_multiply_func)
            print_key_details(args.privatekey, pubx, puby, wif, comp)
        except Exception as e:
            logging.error(f"Error processing key {args.privatekey}: {e}")
    
    elif args.random:
        pk = secrets.randbelow(n - 1) + 1
        _, pubx, puby, _, wif, comp = generate_key_material(pk, ec_multiply_func)
        print_key_details(pk, pubx, puby, wif, comp)
        
    elif args.pubkey:
        try:
            p2pkh, p2sh_p2w, bech = pubkey_to_addresses(args.pubkey)
            print(f"Public Key (Compressed): {args.pubkey}\n" + "-"*25)
            print(f"Address (P2PKH/Legacy):   {p2pkh}\nAddress (P2SH-P2WPKH):    {p2sh_p2w}\nAddress (P2WPKH/Bech32):  {bech}")
        except (ValueError, TypeError):
            logging.error("Invalid public key hex string. Must be a 66-character hex string for a 33-byte compressed key.")
            
    elif args.start is not None:
        if args.end is None: parser.error("--start requires --end.")
        if args.start >= args.end: parser.error("--start value must be less than --end.")
        
        # Adjust chunk size for slow mode
        chunk_size = args.chunk_size if args.fast else min(args.chunk_size, 100)
        logging.info(f"Starting range generation with {'fast' if args.fast else 'slow'} engine.")
        
        process_range_parallel(args.start, args.end, args.output, args.workers, chunk_size, ec_multiply_func, not args.no_y)

if __name__ == "__main__":
    main()