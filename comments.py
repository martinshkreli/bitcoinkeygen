#the generator point is multiplied by the private key, d, to get the public key, Q
#example private key: 112757557418114203588093402336452206775565751179231977388358956335153294300646
# in hex: f94a840f1e1a901843a75dd07ffcc5c84478dc4f987797474c9393ac53ab55e6
#example public key
    #x: 33886286099813419182054595252042348742146950914608322024530631065951421850289
    #in hex: 0x4aeaf55040fa16de37303d13ca1dde85f4ca9baa36e2963a27a1c0c1165fe2b1
    #y: 9529752953487881233694078263953407116222499632359298014255097182349749987176
#convert to hex and concatenate. must be 32 bytes, use prepend 0s if necessary.
# prefix with 04, which includes the full y.
# prefix 02 is if y is even, prefix 03 if y is odd - do not include the y value.

#private = "L2unCh44WZdnhC3FSz6NXF26FPJgqkLjQJAg5pVXQKPPMKafeWr8"
#public = "1Lu4FppuLxLpVorSRPzFaB2SsbzaJohCfG"
#privatekeydecimal = 112757557418114203588093402336452206775565751179231977388358956335153294300646
#private_key = "0FC935FFA185E31A1139856C833EF59B09BEBDE134C00E8B1B2C8E3116E1BEC7"

#privatekeydecimal = 15511464020905377194372854726488703333936648691477104411146025727023874313728
#private_key = (hex(privatekeydecimal)[2:]).upper()
#privatekeydecimal = int(private_key, 16)
#private_key = '18e14a7b6a307f426a94f8114701e7c8e774e7f9a47e2c2035db29a206321725'.upper()

#secp256k1 = y^2=x^3+7
#y = pow(x, -1, p) -- modular multiplicative inverse y=invmod(x,p) such that x*y==1 (mod p)

#mean = np.mean([i[0] for i in list])
    #mean2 = np.mean([i[3] for i in list])
    #print(int(mean), int(mean2), np.max([i[3] for i in list]), np.min([i[3] for i in list]))
    # Batch write to the file after processing all keys for that batch