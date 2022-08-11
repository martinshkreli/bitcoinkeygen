#secp256k1 = y^2=x^3+7
#y = pow(x, -1, p) -- modular multiplicative inverse y=invmod(x,p) such that x*y==1 (mod p)

import numpy as np
import hashlib as hashlib
import base58 as base58
private = "L2unCh44WZdnhC3FSz6NXF26FPJgqkLjQJAg5pVXQKPPMKafeWr8"
public = "1Lu4FppuLxLpVorSRPzFaB2SsbzaJohCfG"
base58array = ['1','2','3','4','5','6','7','8','9','A','B', 'C', 'D', 'E','F','G','H','J','K','L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z','a','b','c','d','e','f','g','h','i','j','k','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
hexarray = ['0', '1','2','3','4','5','6','7','8','9','A','B', 'C', 'D', 'E','F']
p =  2 ** 256 - 2 ** 32 - 2 ** 9 - 2 ** 8 - 2 ** 7 - 2 ** 6 - 2 ** 4 - 1
order =  115792089237316195423570985008687907852837564279074904382605163141518161494337
genX = 55066263022277343669578718895168534326250603453777594175500187360389116729240
genY = 32670510020758816978083085130507043184471273380659243275938904335757337482424

def convertBase58toDecimal(x):    
    return base58array.index(x)

def convertHextoDecimal(x):    
    return hexarray.index(x)

def decimalToBase58(x):
    base10 = 0
    for index, y in enumerate(x):
        base58value = convertBase58toDecimal(y)
        newsummand = base58value * 58**(len(x) - index - 1)
        base10 = base10 + newsummand
    return base10

def hexToBase58(x):
    base10 = 0
    for index, y in enumerate(x):
        base58value = convertHextoDecimal(y)
        newsummand = base58value * 58**(len(x) - index - 1)
        base10 = base10 + newsummand
    return base10

def mmi(x,p):
    return pow(x,-1,p)

def doublepoint(x,y):
    slope=(((3*x**2) * mmi(2*y,p)) )%p
    newx=(slope**2 - 2*x) %p
    newy=((slope*(x - newx)) - y) %p
    return newx,newy

def addpoint(x,y,a,b):
  if(x==a and y==b):
    return doublepoint(x)
  slope=((y-b) * mmi(x-a, p))%p
  returnx = (((slope**2) - x - a)%p)
  returny = (slope* (x - returnx)- y)%p
  return returnx,returny

def multiplypoint(k, genX, genY):
    currentGenX = genX
    currentGenY = genY
    
    binarypoint = (bin(k)[3:])
    binarypointnoslice = (bin(k))
    
    for index, y in enumerate(binarypoint):        
        currentGenX, currentGenY = doublepoint(currentGenX,currentGenY)
        if(y=='1'): 
            currentGenX, currentGenY = addpoint(currentGenX, currentGenY, genX, genY)
    return currentGenX, currentGenY

privatekeydecimal = 112757557418114203588093402336452206775565751179231977388358956335153294300646
pubkeyx, pubkeyy = (multiplypoint(privatekeydecimal, genX, genY))
privatekeyhex = (hex(privatekeydecimal))
privatekeyhex = "80" + privatekeyhex[2:]
print("private key D: ", privatekeydecimal)
print("private key H: ", privatekeyhex)


hexedpubkeyx = (hex(pubkeyx)[2:])
hexedpubkeyy = (hex(pubkeyy)[2:])
convertedlastplace = int(hexedpubkeyy[-1], 16)
appendcode = ""
if convertedlastplace % 2 == 0: appendcode = "02"
if convertedlastplace % 2 == 1: appendcode = "03"

if (len(hexedpubkeyx)) != 64: print("ERROR: NOT 64 length")
if (len(hexedpubkeyy)) != 64: print("ERROR: NOT 64 length")
publickeyhex = appendcode + hexedpubkeyx
print("public key: ", publickeyhex)

privatekeyhex = str("80EBC945C7D20077AB8E4A7599EFCDC83D0E8A2EEDE03A3A9C04A4D85874DA983D")
hashobject = (hashlib.sha256(bytes.fromhex(privatekeyhex)))
firsthashedprivatekey = (hashobject.hexdigest())
secondHashObject = (hashlib.sha256(bytes.fromhex(firsthashedprivatekey)))
secondHashObjectDecoded = (secondHashObject.hexdigest())
fourBytes = secondHashObjectDecoded[:8]
finalprivatekey = (privatekeyhex + fourBytes).upper()
finalprivatekey = (base58.b58encode((bytes.fromhex(finalprivatekey))))
print("WIF private key: ", finalprivatekey)

pubhashobject = (hashlib.sha256(bytes.fromhex(publickeyhex)))
firstpubhashedprivatekey = (pubhashobject.hexdigest())
#ripemd160
secondPubHashObjectDecoded = (secondPubHashObject.hexdigest())
pubFourBytes = secondPubHashObjectDecoded[:8]
finalpublickey = (publickeyhex + pubFourBytes).upper()
finalpublickey = (base58.b58encode((bytes.fromhex(finalpublickey))))
print("WIF public key: ", finalpublickey)