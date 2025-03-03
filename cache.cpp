#include <iostream>
#include <sstream>
#include <iomanip>
#include <string>
#include <vector>
#include <chrono>
#include <stdexcept>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <omp.h>  // OpenMP header

// External libraries: Boost.Multiprecision, OpenSSL, and nlohmann/json.
#include <boost/multiprecision/cpp_int.hpp>
#include <openssl/sha.h>
#include <openssl/ripemd.h>
#include "nlohmann/json.hpp"

using namespace std;
using namespace boost::multiprecision;
using json = nlohmann::json;

// Type alias for an elliptic-curve point.
typedef pair<cpp_int, cpp_int> Point;

// -----------------------------------------------------------------------------
// Global configuration and secp256k1 parameters

const int MAX_KEYS = 1500000;
const int KEY_PROGRESS_INTERVAL = 500000;
const string MAINNET_PRIVATE_KEY_PREFIX = "80";
const string MAINNET_PUBLIC_KEY_PREFIX = "00";

// secp256k1 parameters:
// p = 2^256 - 2^32 - 2^9 - 2^8 - 2^7 - 2^6 - 2^4 - 1
cpp_int p;
cpp_int genX;
cpp_int genY;

// Precomputed lookup table: treeCache[level][index].
// For a key k (>=0) whose binary representation (excluding the leading '1')
// has L bits, the corresponding point is treeCache[L][index] where index = k - (1 << L).
vector<vector<Point>> treeCache;

// Filename for persisting the precomputed tree.
const string TREE_CACHE_FILE = "tree_cache.json";

// -----------------------------------------------------------------------------
// Logging helper (flushes immediately)
void logInfo(const string &msg) {
    auto now = chrono::system_clock::now();
    time_t now_time = chrono::system_clock::to_time_t(now);
    cout << put_time(localtime(&now_time), "%Y-%m-%d %X")
         << " - INFO - " << msg << "\n" << flush;
}

// -----------------------------------------------------------------------------
// Helper: Convert cpp_int to hexadecimal string with optional zero-padding.
string cppIntToHex(const cpp_int &n, int width = 0) {
    stringstream ss;
    ss << hex << n;
    string s = ss.str();
    if (width > (int)s.size())
        s = string(width - s.size(), '0') + s;
    return s;
}

// -----------------------------------------------------------------------------
// Modular Multiplicative Inverse using Extended Euclidean Algorithm.
cpp_int modInverse(cpp_int a, cpp_int mod) {
    cpp_int m0 = mod, t, q;
    cpp_int x0 = 0, x1 = 1;
    if (mod == 1)
        return 0;
    while (a > 1) {
        q = a / mod;
        t = mod;
        mod = a % mod;
        a = t;
        t = x0;
        x0 = x1 - q * x0;
        x1 = t;
    }
    if (x1 < 0)
        x1 += m0;
    return x1;
}

// -----------------------------------------------------------------------------
// Elliptic Curve Operations (point doubling and addition).

Point doublePoint(const cpp_int &x, const cpp_int &y) {
    cpp_int slope = (3 * x * x * modInverse(2 * y, p)) % p;
    if (slope < 0)
        slope += p;
    cpp_int newx = (slope * slope - 2 * x) % p;
    if (newx < 0)
        newx += p;
    cpp_int newy = (slope * (x - newx) - y) % p;
    if (newy < 0)
        newy += p;
    return {newx, newy};
}

Point addPoint(const cpp_int &x, const cpp_int &y, const cpp_int &a, const cpp_int &b) {
    if (x == a && y == b)
        return doublePoint(x, y);
    cpp_int slope = ((y - b) * modInverse(x - a, p)) % p;
    if (slope < 0)
        slope += p;
    cpp_int returnx = (slope * slope - x - a) % p;
    if (returnx < 0)
        returnx += p;
    cpp_int returny = (slope * (x - returnx) - y) % p;
    if (returny < 0)
        returny += p;
    return {returnx, returny};
}

// -----------------------------------------------------------------------------
// Parallelized Tree Building
// Build treeCache for levels 0 to maxL, where maxL = (number of bits in MAX_KEYS) - 1.
void buildTreeCache(int maxKeys) {
    // Determine number of bits in maxKeys.
    int L = 0;
    int temp = maxKeys;
    while (temp > 0) {
        L++;
        temp >>= 1;
    }
    int maxL = L - 1;  // Required treeCache levels = L (levels 0 .. maxL)
    treeCache.resize(maxL + 1);
    // Level 0: only one entry – the generator.
    treeCache[0].resize(1);
    treeCache[0][0] = {genX, genY};
    logInfo("Building treeCache up to level " + to_string(maxL));

    // For each level l from 1 to maxL, compute points in parallel.
    for (int l = 1; l <= maxL; l++) {
        int size = 1 << l;  // 2^l entries.
        treeCache[l].resize(size);
        #pragma omp parallel for schedule(dynamic)
        for (int i = 0; i < size; i++) {
            // Parent index from previous level.
            Point parent = treeCache[l - 1][i >> 1];
            // Always double the parent.
            Point pt = doublePoint(parent.first, parent.second);
            // If the current bit (i & 1) is 1, add the generator.
            if (i & 1)
                pt = addPoint(pt.first, pt.second, genX, genY);
            treeCache[l][i] = pt;
        }
    }
    logInfo("Completed building treeCache up to level " + to_string(maxL));
}

// -----------------------------------------------------------------------------
// Save treeCache to disk in JSON format.
bool saveTreeCache(const string &filename) {
    json j;
    j["levels"] = json::array();
    for (size_t l = 0; l < treeCache.size(); l++) {
        json level = json::array();
        for (size_t i = 0; i < treeCache[l].size(); i++) {
            // Save each point as [x, y] with both as strings.
            level.push_back({ treeCache[l][i].first.str(), treeCache[l][i].second.str() });
        }
        j["levels"].push_back(level);
    }
    ofstream ofs(filename);
    if (!ofs.is_open()) {
        logInfo("Error: Could not open " + filename + " for saving.");
        return false;
    }
    ofs << j.dump();
    ofs.close();
    logInfo("Saved treeCache to " + filename);
    return true;
}

// -----------------------------------------------------------------------------
// Load treeCache from disk (JSON format).
bool loadTreeCache(const string &filename) {
    ifstream ifs(filename);
    if (!ifs.is_open())
        return false;
    json j;
    try {
        ifs >> j;
    } catch (...) {
        logInfo("Error parsing " + filename);
        return false;
    }
    if (!j.contains("levels") || !j["levels"].is_array()) {
        logInfo("Invalid format in " + filename);
        return false;
    }
    vector<vector<Point>> loadedCache;
    for (const auto &level : j["levels"]) {
        if (!level.is_array())
            return false;
        vector<Point> thisLevel;
        for (const auto &pt : level) {
            if (!pt.is_array() || pt.size() != 2)
                return false;
            string xStr = pt[0].get<string>();
            string yStr = pt[1].get<string>();
            thisLevel.push_back({ cpp_int(xStr), cpp_int(yStr) });
        }
        loadedCache.push_back(thisLevel);
    }
    treeCache = loadedCache;
    logInfo("Loaded treeCache with " + to_string(treeCache.size()) + " levels from " + filename);
    return true;
}

// -----------------------------------------------------------------------------
// Multiply point using the precomputed treeCache.
// For key k, if k == 0 return the generator;
// Otherwise, let L = floor(log2(k)) and index = k - (1 << L),
// then return treeCache[L][index].
Point multiplyPoint(int k) {
    if (k == 0)
        return treeCache[0][0];
    int L = 31 - __builtin_clz(k);  // floor_log2(k)
    int pathLength = L;             // because binary representation has (L+1) bits.
    int index = k - (1 << L);       // the "path" as an integer.
    if (pathLength >= (int)treeCache.size())
        throw runtime_error("Key value out of precomputed range.");
    return treeCache[pathLength][index];
}

// -----------------------------------------------------------------------------
// Base58 Encoding (using Boost.Multiprecision for big-integer arithmetic).
string Base58Encode(const vector<unsigned char>& input) {
    const string alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    int zeros = 0;
    while (zeros < (int)input.size() && input[zeros] == 0)
        zeros++;
    cpp_int num = 0;
    for (unsigned char byte : input)
        num = (num << 8) + byte;
    string result;
    while (num > 0) {
        cpp_int rem = num % 58;
        num /= 58;
        result = alphabet[static_cast<int>(rem)] + result;
    }
    for (int i = 0; i < zeros; i++)
        result = '1' + result;
    return result;
}

// -----------------------------------------------------------------------------
// Helper: Convert hexadecimal string to byte vector.
vector<unsigned char> HexToBytes(const string &hex) {
    vector<unsigned char> bytes;
    for (size_t i = 0; i < hex.length(); i += 2) {
        string byteString = hex.substr(i, 2);
        unsigned char byte = (unsigned char) strtol(byteString.c_str(), nullptr, 16);
        bytes.push_back(byte);
    }
    return bytes;
}

// -----------------------------------------------------------------------------
// Structure to hold key data.
struct KeyData {
    string privateKeyDecimal;
    string versionedPrivateKey;
    string privateKeyWIF;
    string pubkeyX;
    string publicKeyHex;
    string binaryAddress;
    string address;
};

// -----------------------------------------------------------------------------
// Generate a Bitcoin key pair and related data.
KeyData generateKey(int privateKeyDecimal) {
    Point pubPoint = multiplyPoint(privateKeyDecimal);

    // Format private key in hexadecimal (zero-padded to 64 characters).
    stringstream ss;
    ss << hex << privateKeyDecimal;
    string hexPrivate = ss.str();
    if (hexPrivate.size() < 64)
        hexPrivate = string(64 - hexPrivate.size(), '0') + hexPrivate;
    string versionedPrivate = MAINNET_PRIVATE_KEY_PREFIX + hexPrivate;

    // Compute checksum for the private key (double SHA256).
    vector<unsigned char> keyBytes = HexToBytes(versionedPrivate);
    unsigned char hash1[SHA256_DIGEST_LENGTH];
    SHA256(keyBytes.data(), keyBytes.size(), hash1);
    unsigned char hash2[SHA256_DIGEST_LENGTH];
    SHA256(hash1, SHA256_DIGEST_LENGTH, hash2);
    stringstream checksumStream;
    for (int i = 0; i < 4; i++)
        checksumStream << hex << setw(2) << setfill('0') << (int)hash2[i];
    string checksum = checksumStream.str();
    string finalKey = versionedPrivate + checksum;
    vector<unsigned char> finalKeyBytes = HexToBytes(finalKey);
    string privateKeyWIF = Base58Encode(finalKeyBytes);

    // Build compressed public key.
    string pubkeyy_hex = cppIntToHex(pubPoint.second);
    char last_char = pubkeyy_hex.back();
    int last_digit = (last_char >= '0' && last_char <= '9') ? last_char - '0' :
                     (last_char >= 'a' && last_char <= 'f') ? last_char - 'a' + 10 :
                     (last_char >= 'A' && last_char <= 'F') ? last_char - 'A' + 10 : 0;
    string appendCode = (last_digit % 2 != 0) ? "03" : "02";
    string pubkeyx_hex = cppIntToHex(pubPoint.first, 64);
    string publicKeyHex = appendCode + pubkeyx_hex;

    // Compute Bitcoin address from the public key.
    vector<unsigned char> publicKeyBytes = HexToBytes(publicKeyHex);
    unsigned char sha256_hash[SHA256_DIGEST_LENGTH];
    SHA256(publicKeyBytes.data(), publicKeyBytes.size(), sha256_hash);
    unsigned char ripemd160_hash[RIPEMD160_DIGEST_LENGTH];
    RIPEMD160(sha256_hash, SHA256_DIGEST_LENGTH, ripemd160_hash);
    vector<unsigned char> versionedRipemd160;
    versionedRipemd160.push_back(0);  // Prepend version byte 0x00.
    for (int i = 0; i < RIPEMD160_DIGEST_LENGTH; i++)
        versionedRipemd160.push_back(ripemd160_hash[i]);
    unsigned char first_sha[SHA256_DIGEST_LENGTH];
    SHA256(versionedRipemd160.data(), versionedRipemd160.size(), first_sha);
    unsigned char second_sha[SHA256_DIGEST_LENGTH];
    SHA256(first_sha, SHA256_DIGEST_LENGTH, second_sha);
    vector<unsigned char> addrBytes = versionedRipemd160;
    for (int i = 0; i < 4; i++)
        addrBytes.push_back(second_sha[i]);
    stringstream ss_addr;
    for (unsigned char byte : addrBytes)
        ss_addr << hex << setw(2) << setfill('0') << (int)byte;
    string binaryAddress = ss_addr.str();
    string address = Base58Encode(addrBytes);

    KeyData kd;
    kd.privateKeyDecimal = to_string(privateKeyDecimal);
    kd.versionedPrivateKey = versionedPrivate;
    kd.privateKeyWIF = privateKeyWIF;
    kd.pubkeyX = pubPoint.first.str();
    kd.publicKeyHex = publicKeyHex;
    kd.binaryAddress = binaryAddress;
    kd.address = address;
    return kd;
}

// -----------------------------------------------------------------------------
// Main function.
int main() {
    // Initialize secp256k1 parameters.
    p = (cpp_int(1) << 256) - (cpp_int(1) << 32) - (cpp_int(1) << 9)
        - (cpp_int(1) << 8) - (cpp_int(1) << 7) - (cpp_int(1) << 6)
        - (cpp_int(1) << 4) - 1;
    genX = cpp_int("55066263022277343669578718895168534326250603453777594175500187360389116729240");
    genY = cpp_int("32670510020758816978083085130507043184471273380659243275938904335757337482424");

    // Try to load treeCache from disk.
    bool loaded = loadTreeCache(TREE_CACHE_FILE);
    // Compute required levels based on MAX_KEYS.
    int requiredLevels = 0;
    {
        int temp = MAX_KEYS;
        while (temp > 0) {
            requiredLevels++;
            temp >>= 1;
        }
    }
    // If loaded treeCache has fewer levels than required, rebuild.
    if (!loaded || (int)treeCache.size() < requiredLevels) {
        logInfo("Loaded treeCache is insufficient (has " + to_string(treeCache.size())
                + " levels, required " + to_string(requiredLevels)
                + "). Rebuilding treeCache...");
        buildTreeCache(MAX_KEYS);
        if (!saveTreeCache(TREE_CACHE_FILE))
            logInfo("Warning: Failed to save treeCache to disk.");
    } else {
        logInfo("Successfully loaded treeCache from disk.");
    }

    logInfo("Generating first " + to_string(MAX_KEYS) + " Bitcoin key pairs...");
    auto start = chrono::high_resolution_clock::now();

    // Parallel key generation using OpenMP.
    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < MAX_KEYS; i++) {
        KeyData keyData = generateKey(i);
        // (Optionally, process or store keyData here.)
        if ((i + 1) % KEY_PROGRESS_INTERVAL == 0) {
            #pragma omp critical
            {
                auto now = chrono::high_resolution_clock::now();
                double elapsed = chrono::duration<double>(now - start).count();
                double keysPerSec = (i + 1) / elapsed;
                logInfo("Generated " + to_string(i + 1) + " keys (" + to_string(keysPerSec) + " keys/sec)");
            }
        }
    }
    return 0;
}
