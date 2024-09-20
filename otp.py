import random
def genotp():
    otp=''
    cap=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    small=[chr(i) for i in range(ord('a'),ord('z')+1)]
    for i in range(0,1):
        otp=otp+random.choice(cap)
        otp=otp+str(random.randint(0,9))
        otp=otp+random.choice(small)
    return otp
