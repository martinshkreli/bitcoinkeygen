import base58

def convertBase58toDecimal(x):    
    return base58array.index(x)

def convertHextoDecimal(x):    
    return hexarray.index(x)

base58array = ['1','2','3','4','5','6','7','8','9','A','B','C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
hexarray = ['0', '1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']

def decimalToBase58(x):
    return base58.b58decode_int(x)

def hexToBase58(x):
    return base58.b58encode_int(int(x, 16))

def process_address(generated_keys):
    for key in generated_keys:
        if key[6] in addlist_set:
            print(key)
            print('FOUND ONE!')
            input('press enter to continue')