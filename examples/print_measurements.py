"""
Connect to the scope and print the full set of statistics for channel 1.

Run it with:   python print_measurements.py
(Make sure dos1104.py is in the folder above this one, or installed.)
"""

import sys
import os

# Allow running this example without installing anything: look for dos1104.py
# in the parent folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dos1104 import DOS1104

CHANNEL = 1

with DOS1104.connect() as scope:
    print("Connected to:", scope.idn())
    print()
    stats = scope.stats(CHANNEL)
    print("Statistics for channel %d:" % CHANNEL)
    for name, value in stats.items():
        print("  %-12s = %s" % (name, value))
