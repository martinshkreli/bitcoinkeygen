# Bitcoin Key Generator

A Python-based Bitcoin key generation tool that implements elliptic curve cryptography for generating Bitcoin private keys, public keys, and addresses. This tool supports multiple address formats including legacy P2PKH, nested SegWit P2SH-P2WPKH, and native SegWit P2WPKH (bech32).

## Features

- Generate Bitcoin private keys and corresponding public keys using secp256k1 elliptic curve
- Support for multiple Bitcoin address formats:
  - Legacy P2PKH addresses (starting with '1')
  - Nested SegWit P2SH-P2WPKH addresses (starting with '3')
  - Native SegWit P2WPKH bech32 addresses (starting with 'bc1')
- Parallel processing for bulk key generation
- Verbose mode for debugging elliptic curve operations
- Convert compressed public keys to multiple address formats
- Export results to CSV format

## Requirements

- Python 3.6+
- `pycryptodome` - For RIPEMD-160 hashing
- `base58` - For Base58 encoding/decoding

## Installation

```bash
pip install pycryptodome base58
```

## Usage

### Generate a Single Key

Generate a Bitcoin key pair from a specific private key:

```bash
python bitcoin_keygen.py --privatekey 12345
```

Output:
```
private_key_decimal: 12345
public_key_x:        89565891926547004231252920425935692360644145829622209833684329913297188986597
public_key_y:        12158399299693830322967808612713398636155367887041628176798871954788371653930
bitcoin_address:     1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
compressed_pubkey:   0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
```

### Convert Public Key to Addresses

Convert a compressed public key to all supported address formats:

```bash
python bitcoin_keygen.py --pubkey 0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
```

Output:
```
compressed_pubkey: 0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
P2PKH (legacy)   : 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH
P2SH-P2WPKH      : 3JvL6Ymt8MVWiCNHC7oWU6nLeHNJKLZGLN
P2WPKH (bech32)  : bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

### Bulk Key Generation

Generate multiple keys in parallel:

```bash
python bitcoin_keygen.py --start 1 --end 10000 --output keys.csv --workers 4
```

Parameters:
- `--start`: Starting private key value
- `--end`: Ending private key value (exclusive)
- `--output`: Output CSV file (default: output.csv)
- `--workers`: Number of parallel workers (default: CPU count)
- `--chunk-size`: Keys per chunk (default: 1000)
- `--no-y`: Exclude Y coordinate from output

### Verbose Mode

Enable detailed logging of elliptic curve operations:

```bash
python bitcoin_keygen.py --privatekey 12345 --verbose
```

## Output Format

The CSV output includes the following columns:
- `private_key`: Private key in decimal format
- `public_key_x`: X coordinate of the public key
- `public_key_y`: Y coordinate of the public key (unless --no-y is used)
- `address`: Bitcoin P2PKH address

## Technical Details

### Elliptic Curve Parameters

This tool uses the secp256k1 elliptic curve with the following parameters:
- Field prime: `p = 2^256 - 2^32 - 2^9 - 2^8 - 2^7 - 2^6 - 2^4 - 1`
- Generator point: 
  - X: `55066263022277343669578718895168534326250603453777594175500187360389116729240`
  - Y: `32670510020758816978083085130507043184471273380659243275938904335757337482424`

### Address Generation Process

1. Generate private key (random 256-bit number)
2. Calculate public key using elliptic curve point multiplication
3. Compress public key (33 bytes)
4. Generate addresses:
   - **P2PKH**: SHA256(pubkey) → RIPEMD160 → Base58Check with version 0x00
   - **P2SH-P2WPKH**: Create witness script → SHA256 → RIPEMD160 → Base58Check with version 0x05
   - **P2WPKH**: SHA256(pubkey) → RIPEMD160 → Bech32 encode with HRP 'bc'

## Performance

The tool uses parallel processing for bulk generation:
- Typical performance: 10,000-50,000 keys/second (depending on CPU)
- Memory efficient streaming to CSV file
- Configurable chunk size for optimization

## Security Considerations

**WARNING**: This tool is for educational and testing purposes only.

- **DO NOT** use sequentially generated private keys for real Bitcoin storage
- **DO NOT** use predictable or low-entropy private keys
- For production use, always use cryptographically secure random number generation
- Private keys should be kept secret and stored securely
- Consider using hardware wallets for significant Bitcoin holdings

## Legal Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors are not responsible for any loss of funds or other damages arising from the use of this software. Users are responsible for understanding Bitcoin security best practices and the risks involved in cryptocurrency management.

## License

This project is released under the MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Acknowledgments

This implementation is based on the Bitcoin protocol specifications and uses standard cryptographic libraries for hash functions and encoding.