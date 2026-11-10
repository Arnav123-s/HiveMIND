"""One lock for the CPU: every model call, member or cell, takes turns.

llama.cpp uses every core for one call; two calls at once (two swarms, or a cell beside a member) oversubscribe the
cores and both slow down badly (a cell eval next to a hive run made no progress in 21 CPU-minutes). Swarms running at
once overlap their waiting (web pages, the browser, programs running), never their model compute.
Re-entrant, so a member's code may call a cell while it holds the lock.
"""
import threading

LOCK = threading.RLock()
