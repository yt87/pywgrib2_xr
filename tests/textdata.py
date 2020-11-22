import sys

import numpy as np

textfile = sys.argv[1]

with open(textfile) as fp:
    s = fp.read()

line, rest = s.split("\n", 1)
chunks = rest.split(line)

nx, ny = [int(_) for _ in line.split()]
u = np.fromstring(chunks[0], sep="\n").reshape(ny, nx)
print(u[-2:, -2:])
if len(chunks) == 2:
    v = np.fromstring(chunks[1], sep="\n").reshape(ny, nx)
    print(v[-2:, -2:])
