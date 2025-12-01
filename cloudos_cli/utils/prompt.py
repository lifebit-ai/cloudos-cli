import sys
import os


def smart_input():

    print("> ", end="", flush=True)
    name = sys.stdin.readline().strip()
    return name