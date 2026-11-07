from typing import TypeVarTuple
from collections import deque

Ts = TypeVarTuple('Ts')

def sort(l: list[tuple[*Ts]]) -> list[tuple[*Ts]]:
    queue2 = deque([l])
    i = 0
    while True:
        queue1 = queue2.copy()
        while len(queue1) > 0:
            L = queue1.pop()
            for j in range(len(L)):
                A = L[j]

        if len(queue2) != 0:
            break


    return l