# hanmatek-dos1104-py

A small, easy-to-read **Python driver for the Hanmatek DOS1104** oscilloscope
(4-channel, 100 MHz). It talks to the scope over USB and lets you read
measurements, compute statistics, and download waveforms from your PC.

The DOS1104 uses the **Owon SDS1104** SCPI command set, so this driver will
**probably also work with the Owon SDS1104 and its rebadges** - but it has only
been **tested on a Hanmatek DOS1104 (firmware V1.2.0)**. If you try it on another
model, please open an issue and say whether it worked.

Everything is in a single file, [`dos1104.py`](dos1104.py), with plain-language
comments. You do not need to be a Python expert to use it.

---

## The #1 thing: getting the scope to show up

Most people get stuck here, and it is not documented anywhere. Do this **on the
scope**, in order:

1. **Set the USB mode to USBTMC:** `Utility` > `Function` > `Configure` >
   `Device` > choose **`USBTMC`**.
2. **Use the correct port:** plug the USB cable into the **USB-Device port on the
   right side panel**. The flat USB-A port on the front is only for a memory
   stick - it will *not* connect to a PC.
3. Plug into the PC.

If you skip step 1 the scope does not appear on the USB bus at all (no device,
not even an "unknown device").

On **Windows** you also need a VISA runtime so Python can talk USBTMC. The
simplest is **NI-VISA** (free from National Instruments). Install it once.

---

## Install

```bash
pip install pyvisa numpy
```

Then copy `dos1104.py` next to your script (or into your project).

---

## Quick start

```python
from dos1104 import DOS1104

# Auto-find the scope over USB
scope = DOS1104.connect()
print(scope.idn())                 # e.g. HANMATEK,DOS1104,24410064,V1.2.0

# Read a measurement from channel 1
print("Vpp:", scope.measure(1, "vpp"), "V")
print("Frequency:", scope.measure(1, "freq"), "Hz")

# Get a full set of statistics in one call
print(scope.stats(1))

# Download the waveform and do whatever you want with it
wave = scope.capture(1)            # screen view (~1500 points)
print(wave["volts"][:10])          # first 10 voltage samples
print(wave["time"][:10])           # matching time values (seconds)

scope.close()
```

Or let it close itself:

```python
from dos1104 import DOS1104

with DOS1104.connect() as scope:
    print(scope.stats(1))
```

See the [`examples/`](examples) folder for runnable scripts (print
measurements, save a waveform to CSV).

---

## What you can do

**Measurements** (read straight from the scope):

```python
scope.measure(ch, "vpp")        # peak-to-peak voltage
scope.measure(ch, "vamp")       # amplitude (top - base)
scope.measure(ch, "vtop")       # top / "vbase" = base
scope.measure(ch, "freq")       # frequency      "period" = period
scope.measure(ch, "rtime")      # rise time
scope.measure(ch, "pwidth")     # +pulse width   "nwidth" = -pulse width
scope.measure(ch, "pduty")      # +duty %        "nduty"  = -duty %
scope.measure(ch, "overshoot")  # overshoot %    "preshoot" = preshoot %
```

**Statistics** - `scope.stats(ch)` returns a dictionary with everything above
**plus** values the firmware does not provide, computed from the waveform:

```
vmax, vmin, vpp, vmean, vrms   (computed here)
vamp, vtop, vbase, freq, period, rtime, pwidth, nwidth,
pduty, nduty, overshoot, preshoot   (from the scope)
```

**Waveforms:**

```python
scope.capture(ch)        # the on-screen wave (~1500 points, fast)
scope.capture_deep(ch)   # the deep-memory record (thousands of points)
```
Both return `time`, `volts`, `raw` (ADC codes) and the scope settings.

**Control:**

```python
scope.run()              # start acquiring
scope.stop()             # freeze
scope.autoset()          # auto-scale to the signal
scope.timebase()         # seconds per division
scope.channel_scale(ch)  # volts per division
scope.screenshot("shot.bmp")   # save the screen (not on all firmware)
```

---

## How voltages are calibrated

The scope sends each sample as a 16-bit number (an "ADC code"). To convert a
code to volts:

```
volts = code * volts_per_division / 6400
```

`6400` means **6400 codes per vertical division**. This was measured directly: a
known **2.0 Vpp** signal produced exactly 6400 codes per division, and the
converted values match the scope's own Vpp reading. So it is verified, not a
guess. It lives in `dos1104.py` as `CODES_PER_DIV` if you ever need to change it.

A full list of every SCPI command the scope understands, with an explanation of
each one, is in **[SCPI_COMMANDS.md](SCPI_COMMANDS.md)**.

---

## Troubleshooting

- **Scope not found / not in Device Manager:** you missed the USBTMC menu step
  above, or you are on the front USB-A port. Fix the menu + port, then replug.
- **Everything times out after a stopped program:** a half-finished waveform
  download can leave the USB link out of sync. **Unplug and replug the scope's
  USB** (or power-cycle it) and it works again. The driver also clears the link
  on connect and after failures to avoid this.
- **`screenshot()` times out:** the bitmap command is not implemented on every
  firmware build. The waveform download (`capture` / `capture_deep`) is the
  reliable way to get the trace.

---

## License

MIT - see [LICENSE](LICENSE). Do whatever you like with it.

This is an independent, community driver. It is not affiliated with Hanmatek or
Owon. The driver code is original; the SCPI command names come from the public
manuals and from observing the scope's own behavior.
