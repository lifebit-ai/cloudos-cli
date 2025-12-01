import sys
import os


def smart_input():

    print("Enter your name: ", end="", flush=True)
    name = sys.stdin.readline().strip()
    print("Hello,", name)
    return name