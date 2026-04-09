def convert2ascii(s):
    return "".join(c for c in s if ord(c) < 128)
