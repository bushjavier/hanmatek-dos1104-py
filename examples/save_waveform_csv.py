"""
Download a waveform and save it to a CSV file (time, volts) you can open in
Excel or plot later.

Run it with:   python save_waveform_csv.py
Change CHANNEL or set DEEP = True for the longer deep-memory record.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dos1104 import DOS1104

CHANNEL = 1
DEEP = False                 # True = deep memory (more points, slower)
OUTPUT = "waveform.csv"

with DOS1104.connect() as scope:
    print("Connected to:", scope.idn())
    wave = scope.capture_deep(CHANNEL) if DEEP else scope.capture(CHANNEL)

    print("Got %d points at %.0f samples/second."
          % (wave["volts"].size, wave["samplerate"]))

    # Write a two-column CSV: time in seconds, voltage in volts.
    with open(OUTPUT, "w") as f:
        f.write("time_s,volts\n")
        for t, v in zip(wave["time"], wave["volts"]):
            f.write("%.9g,%.6g\n" % (t, v))

    print("Saved to", os.path.abspath(OUTPUT))
