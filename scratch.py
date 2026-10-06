import re

arr = "/cases/acme/memo(1)"

left, right = arr.split('(')

print(f'L {left} R {right}')