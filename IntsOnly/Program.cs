using System;
using System.Numerics;
using System.Diagnostics;
using System.Threading.Tasks;

class ECC
{
    private static BigInteger p = BigInteger.Parse("115792089237316195423570985008687907853269984665640564039457584007908834671663");
    private static BigInteger genX = BigInteger.Parse("55066263022277343669578718895168534326250603453777594175500187360389116729240");
    private static BigInteger genY = BigInteger.Parse("32670510020758816978083085130507043184471273380659243275938904335757337482424");
    private static readonly BigInteger inv2 = ModInverse(2, p);

    private static BigInteger ModInverse(BigInteger value, BigInteger modulus)
    {
        return BigInteger.ModPow(value, modulus - 2, modulus);
    }

    private static (BigInteger, BigInteger) DoublePoint(BigInteger x, BigInteger y)
    {
        BigInteger slope = (3 * BigInteger.Pow(x, 2) * inv2) % p;
        BigInteger newX = (BigInteger.Pow(slope, 2) - 2 * x) % p;
        BigInteger newY = (slope * (x - newX) - y) % p;
        return (newX, newY);
    }

    private static (BigInteger, BigInteger) AddPoint(BigInteger x1, BigInteger y1, BigInteger x2, BigInteger y2)
    {
        if (x1 == x2 && y1 == y2)
            return DoublePoint(x1, y1);

        BigInteger slope = ((y2 - y1) * ModInverse(x2 - x1, p)) % p;
        BigInteger newX = (BigInteger.Pow(slope, 2) - x1 - x2) % p;
        BigInteger newY = (slope * (x1 - newX) - y1) % p;
        return (newX, newY);
    }

    private static (BigInteger, BigInteger) MultiplyPoint(BigInteger k, BigInteger genX, BigInteger genY)
    {
        BigInteger currentX = genX, currentY = genY;
        string binaryK = Convert.ToString((long)k, 2).Substring(1);

        foreach (char bit in binaryK)
        {
            (currentX, currentY) = DoublePoint(currentX, currentY);
            if (bit == '1')
                (currentX, currentY) = AddPoint(currentX, currentY, genX, genY);
        }

        return (currentX, currentY);
    }

    private static BigInteger[] Generate(BigInteger privateKey)
    {
        (BigInteger pubX, BigInteger pubY) = MultiplyPoint(privateKey, genX, genY);
        return new BigInteger[] { privateKey, pubX };
    }

    public static void Main()
    {
        int totalKeys = 10000;
        Stopwatch stopwatch = Stopwatch.StartNew();

        Parallel.For(1, totalKeys + 1, num => {
            BigInteger[] result = Generate(num);
        });

        stopwatch.Stop();
        Console.WriteLine("Elapsed time: {0} ms", stopwatch.ElapsedMilliseconds);
    }
}
