from time import time

p =  2 ** 256 - 2 ** 32 - 2 ** 9 - 2 ** 8 - 2 ** 7 - 2 ** 6 - 2 ** 4 - 1
order =  115792089237316195423570985008687907852837564279074904382605163141518161494337 # n, supposed to be less than P, 78 DIGITS;
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424

from time import time
import gmpy2
from gmpy2 import mpz
p = mpz(2**256 - 2**32 - 2**9 - 2**8 - 2**7 - 2**6 - 2**4 - 1)
inv_2 = gmpy2.invert(mpz(2), p)

def doublepoint(x, y):
    x = mpz(x)
    y = mpz(y)
    slope = (3 * x**2 * inv_2) % p
    newx = (slope**2 - 2*x) % p
    newy = (slope*(x - newx) - y) % p
    return newx, newy

def addpoint(x, y, a, b):
    x, y, a, b = map(mpz, (x, y, a, b))
    if x == a and y == b:
        return doublepoint(x, y)
    slope = ((y - b) * gmpy2.invert(x - a, p)) % p
    returnx = (slope**2 - x - a) % p
    returny = (slope * (x - returnx) - y) % p
    return returnx, returny

def multiplypoint(k, genX, genY):
    currentGenX = mpz(genX)
    currentGenY = mpz(genY)
    binarypoint = bin(k)[3:]    
    for y in binarypoint:
        currentGenX, currentGenY = doublepoint(currentGenX, currentGenY)
        if y == '1':
            currentGenX, currentGenY = addpoint(currentGenX, currentGenY, genX, genY)
    return currentGenX, currentGenY

def generate(privatekeydecimal):
    pubkeyx, pubkeyy = multiplypoint(privatekeydecimal, genX, genY)
    return [privatekeydecimal, pubkeyx]

import multiprocessing
from time import time
import gmpy2
from gmpy2 import mpz

def generate(privatekeydecimal):
    pubkeyx, pubkeyy = multiplypoint(privatekeydecimal, genX, genY)
    return [privatekeydecimal, pubkeyx]

def worker(start, end):
    results = []
    for num in range(start, end):
        results.append(generate(num))
    return results

def main():
    num_processes = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=num_processes)
    print("Number of processes: ", num_processes)
    total_keys = 1000000
    range_size = total_keys // num_processes
    ranges = [(i * range_size + 1, (i + 1) * range_size + 1) for i in range(num_processes)]
    start_time = time()
    results = pool.starmap(worker, ranges)
    pool.close()
    pool.join()
    print("--- %s seconds ---" % (time() - start_time))


if __name__ == '__main__':
    main()
