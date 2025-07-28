import logging
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
from Crypto.Hash import RIPEMD
import base58
import time

p = 2**256 - 2**32 - 2**9 - 2**8 - 2**7 - 2**6 - 2**4 - 1
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424
CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def _bech32_polymod(vals):
    g = [0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3]
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
    polymod = _bech32_polymod(values + [0,0,0,0,0,0]) ^ 1
    checksum = [(polymod >> 5*(5-i)) & 31 for i in range(6)]
    return hrp + '1' + ''.join(CHARSET[d] for d in data + checksum)

def pubkey_to_addresses(pubkey_hex):
    """Return (P2PKH, P2SH‑P2WPKH, P2WPKH) for a compressed pubkey hex."""
    pk = bytes.fromhex(pubkey_hex)
    h160 = RIPEMD.new(sha256(pk).digest()).digest()

    # legacy P2PKH  (version 0x00)
    p2pkh = base58.b58encode_check(b'\x00' + h160).decode()

    # nested SegWit P2SH‑P2WPKH  (redeemScript = 0x0014{h160})
    redeem = b'\x00\x14' + h160
    h160_r = RIPEMD.new(sha256(redeem).digest()).digest()
    p2sh_p2w = base58.b58encode_check(b'\x05' + h160_r).decode()

    # native SegWit P2WPKH  (bech32 HRP 'bc', version 0)
    bech = bech32_encode('bc', 0, h160)

    return p2pkh, p2sh_p2w, bech

def mmi(x, p=p):
    return pow(x, -1, p)

def doublepoint(x, y):
    slope = (3 * x * x * mmi(2 * y)) % p
    return ((slope * slope - 2 * x) % p, (slope * (x - (slope * slope - 2 * x) % p) - y) % p)

def addpoint(x1, y1, x2, y2):
    if x1 == x2 and y1 == y2:
        return doublepoint(x1, y1)
    slope = ((y1 - y2) * mmi(x1 - x2)) % p
    newx  = (slope * slope - x1 - x2) % p
    newy  = (slope * (x1 - newx) - y1) % p
    return newx, newy

def multiplypoint(k, gx=genX, gy=genY):
    x, y = gx, gy
    for bit in bin(k)[3:]:
        x, y = doublepoint(x, y)
        if bit == '1':
            x, y = addpoint(x, y, gx, gy)
    return x, y

def generate(privatekeydecimal):
    pubx, puby = multiplypoint(privatekeydecimal)
    priv_bytes = privatekeydecimal.to_bytes(32, 'big')
    wif        = base58.b58encode_check(b'\x80' + priv_bytes + b'\x01').decode()
    prefix     = b'\x02' if (puby & 1)==0 else b'\x03'
    sha_digest = sha256(prefix + pubx.to_bytes(32, 'big')).digest()
    ripe       = RIPEMD.new(sha_digest).digest()
    addr       = base58.b58encode_check(b'\x00' + ripe).decode()
    # Return Y coordinate as well
    return privatekeydecimal, pubx, puby, addr

def mmi_verbose(x, p=p):
    inv = pow(x, -1, p)
    logging.debug(f"mmi({x}) → {inv}")
    return inv

def doublepoint_verbose(x, y):
    logging.debug(f"doublepoint start: ({x}, {y})")
    slope = (3 * x * x * mmi_verbose(2 * y)) % p
    newx  = (slope * slope - 2 * x) % p
    newy  = (slope * (x - newx) - y) % p
    logging.debug(f"doublepoint result: slope={slope}, new=({newx},{newy})")
    return newx, newy

def addpoint_verbose(x1, y1, x2, y2):
    logging.debug(f"addpoint start: P1=({x1},{y1}), P2=({x2},{y2})")
    if x1 == x2 and y1 == y2:
        return doublepoint_verbose(x1, y1)
    slope = ((y1 - y2) * mmi_verbose(x1 - x2)) % p
    newx  = (slope * slope - x1 - x2) % p
    newy  = (slope * (x1 - newx) - y1) % p
    logging.debug(f"addpoint result: slope={slope}, new=({newx},{newy})")
    return newx, newy

def multiplypoint_verbose(k, gx=genX, gy=genY):
    logging.info(f"Starting multiplypoint_verbose(k={k})")
    x, y = gx, gy
    print(bin(k)[3:])
    for idx, bit in enumerate(bin(k)[3:], start=1):
        print('idx, bit: ', idx, bit)
        logging.debug(f"[{idx}] doubling ({x},{y})")
        x, y = doublepoint_verbose(x, y)
        if bit == '1':
            logging.debug(f"[{idx}] adding generator ({gx},{gy})")
            x, y = addpoint_verbose(x, y, gx, gy)
    logging.info(f"Result of multiplypoint_verbose: ({x},{y})")
    return x, y

def generate_verbose(privatekeydecimal):
    pubx, puby = multiplypoint_verbose(privatekeydecimal)
    logging.debug(f"Public key coords: x={pubx}, y={puby}")
    priv_bytes = privatekeydecimal.to_bytes(32, 'big')
    wif        = base58.b58encode_check(b'\x80' + priv_bytes + b'\x01').decode()
    prefix     = b'\x02' if (puby & 1)==0 else b'\x03'
    sha_digest = sha256(prefix + pubx.to_bytes(32, 'big')).digest()
    ripe       = RIPEMD.new(sha_digest).digest()
    addr       = base58.b58encode_check(b'\x00' + ripe).decode()
    logging.info(f"WIF={wif}, address={addr}")
    # Return Y coordinate as well
    return privatekeydecimal, pubx, puby, addr

def chunked_range(start, end, chunk_size):
    for i in range(start, end, chunk_size):
        yield (i, min(i + chunk_size, end))

def process_chunk(chunk, gen_func):
    s, e = chunk
    out = []
    for i in range(s, e):
        result = gen_func(i)
        if len(result) == 4:  # New format with Y
            priv, pubx, puby, addr = result
            out.append(f"{priv},{pubx},{puby},{addr}\n")
        else:  # Old format without Y (backward compatibility)
            priv, pubx, addr = result
            out.append(f"{priv},{pubx},{addr}\n")
    return "".join(out)

def process_range_parallel(start, end, output, workers, chunk_size, gen_func, include_y=True):
    total = end - start
    chunks = list(chunked_range(start, end, chunk_size))
    t0 = time.time()
    
    # Write header if file is new
    try:
        with open(output, 'x') as f:
            if include_y:
                f.write("private_key,public_key_x,public_key_y,address\n")
            else:
                f.write("private_key,public_key_x,address\n")
    except FileExistsError:
        pass
    
    with ProcessPoolExecutor(max_workers=workers) as exe, open(output, 'a', buffering=1<<20) as f:
        futures = {exe.submit(process_chunk, c, gen_func): c for c in chunks}
        done = 0
        for fut in as_completed(futures):
            data = fut.result()
            f.write(data)
            done += (futures[fut][1] - futures[fut][0])
            logging.info(f"Progress: {done}/{total}")
    elapsed = time.time() - t0
    print(f"Completed {total} keys in {elapsed:.2f}s ⇒ {total/elapsed:.2f} keys/sec")

def main():
    parser = argparse.ArgumentParser("Bitcoin keygen")
    parser.add_argument("--privatekey", type=int)
    parser.add_argument("--start",      type=int)
    parser.add_argument("--end",        type=int)
    parser.add_argument("--output",     type=str,   default="output.csv")
    parser.add_argument("--workers",    type=int,   default=None)
    parser.add_argument("--chunk-size", type=int,   default=1_000)
    parser.add_argument("-v", "--verbose", action="store_true", help="log every EC step (slower!)")
    parser.add_argument("--no-y", action="store_true", help="Don't include Y coordinate in output")
    parser.add_argument("--pubkey", type=str, help="33‑byte compressed pubkey hex → print 3 addresses")

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    gen_func = generate_verbose if args.verbose else generate

    if args.privatekey is not None:
        result = gen_func(args.privatekey)
        if len(result) == 4:
            priv, pubx, puby, addr = result
            print("private_key_decimal:", priv)
            print("public_key_x:       ", pubx)
            print("public_key_y:       ", puby)
            print("bitcoin_address:    ", addr)
            
            # Also show compressed public key format
            prefix = '02' if (puby & 1) == 0 else '03'
            compressed = prefix + format(pubx, '064x')
            print("compressed_pubkey:  ", compressed)
    elif args.pubkey:
        p2pkh, p2sh, bech = pubkey_to_addresses(args.pubkey)
        print("compressed_pubkey:", args.pubkey)
        print("P2PKH (legacy)   :", p2pkh)
        print("P2SH‑P2WPKH      :", p2sh)
        print("P2WPKH (bech32)  :", bech)
        return
    elif args.start is not None and args.end is not None:
        process_range_parallel(args.start, args.end, args.output, args.workers, args.chunk_size, gen_func, not args.no_y)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()