"""
dos1104.py - Python driver for the Hanmatek DOS1104 oscilloscope.

The DOS1104 is a 4-channel scope that speaks the Owon SDS1104 SCPI dialect over
USB (USBTMC). It lets you, from a PC:

  * read measurements (Vpp, Vamp, Vtop, frequency, duty, ...)
  * compute full statistics from the captured wave (Vmax, Vmin, Vmean, Vrms)
  * download the waveform (screen view, or the deeper memory record)
  * run / stop / autoset the scope

It only needs `pyvisa` (talks USBTMC) and `numpy` (handles the sample arrays):
    pip install pyvisa numpy

IMPORTANT - getting the scope to show up on the PC (the part nobody documents):
  1. On the scope: Utility > Function > Configure > Device > set it to "USBTMC".
  2. Use the USB-Device port on the RIGHT side panel (not the front USB-A, that
     one is only for a memory stick).
  3. Plug into the PC. On Windows you also need a VISA runtime installed
     (NI-VISA is a common one). Then this driver finds the scope automatically.

Tested with a Hanmatek DOS1104 (firmware V1.2.0). It very likely also works with
other scopes of the same family (Owon SDS1104 and rebadges), but that is not
verified - tell me if it works for yours!
"""

import json
import re

import numpy as np
import pyvisa

# --- The voltage calibration constant -------------------------------------
# The scope sends each waveform sample as a 16-bit number (an "ADC code").
# To turn a code into volts you use the channel's volts-per-division and this
# constant: 6400 codes = 1 vertical division.
#     volts = code * volts_per_division / 6400
# This was measured directly: a known 2.0 Vpp signal gave exactly 6400 codes
# per division, and the result matches the scope's own Vpp reading. So it is
# verified, not a guess.
CODES_PER_DIV = 6400.0

# The scope shows up on USB with this vendor/product id (and a couple of
# alternates seen in the wild). We try them in order when auto-detecting.
USB_PATTERNS = ("?*::0x5345::0x1235::?*", "?*::21317::4661::?*")

# Map a short name -> the SCPI word the firmware understands.
# These are the measurements the DOS1104 firmware actually answers.
# (It does NOT answer Vmax/Vmin/Vmean/Vrms - use stats() for those.)
MEASUREMENTS = {
    "vpp": "PKPK",          # peak-to-peak voltage
    "vamp": "VAMP",         # amplitude (top - base)
    "vtop": "VTOP",         # top (flat high level)
    "vbase": "VBAS",        # base (flat low level)
    "freq": "FREQ",         # frequency
    "period": "PER",        # period
    "rtime": "RTIME",       # rise time
    "pwidth": "PWIDTH",     # positive pulse width
    "nwidth": "NWIDTH",     # negative pulse width
    "pduty": "PDUTY",       # positive duty cycle (%)
    "nduty": "NDUTY",       # negative duty cycle (%)
    "overshoot": "OVERSHOOT",
    "preshoot": "PRESHOOT",
}

# Units the scope appends to replies, and what to multiply by to get base SI
# units (volts, seconds, hertz).
UNITS = {
    "uV": 1e-6, "mV": 1e-3, "V": 1.0,
    "Hz": 1.0, "kHz": 1e3, "KHz": 1e3, "MHz": 1e6,
    "ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0,
    "%": 1.0, "": 1.0,
}


def _clean(reply):
    """The scope ends every reply with '->'. Remove it and trim spaces."""
    return reply.replace("->", "").strip()


def _to_number(reply):
    """
    Turn a scope reply into a plain number in base units.

    The scope answers measurements as text like 'Vpp : 2.040V' or 'F : 1.000KHz'
    or 'T :   ?' (the '?' means it cannot measure it right now). This pulls out
    the number and applies the unit. Returns None when there is no valid value.
    """
    text = _clean(reply)
    if ":" in text:                 # drop the label part ("Vpp :")
        text = text.split(":", 1)[1].strip()
    if "?" in text or text == "":
        return None
    match = re.match(r"([-+]?[0-9]*\.?[0-9]+)\s*([a-zA-Z%]*)", text)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    return number * UNITS.get(unit, 1.0)


class DOS1104:
    """
    A connection to one DOS1104 scope.

    Basic use (auto-find the scope):

        scope = DOS1104.connect()
        print(scope.idn())
        print(scope.measure(1, "vpp"))     # peak-to-peak on channel 1
        data = scope.capture(1)            # download channel 1 waveform
        scope.close()

    Or with a 'with' block so it closes itself:

        with DOS1104.connect() as scope:
            print(scope.stats(1))
    """

    def __init__(self, instrument, resource_manager=None):
        # 'instrument' is the open pyvisa connection. You normally do not create
        # this yourself - use DOS1104.connect().
        self.inst = instrument
        self._rm = resource_manager

    # ---------------------------------------------------------------- connect
    @classmethod
    def connect(cls, resource=None, timeout_ms=5000):
        """
        Open a connection to the scope.

        resource:  leave it None to auto-detect by USB id, or pass a VISA
                   address string like 'USB0::0x5345::0x1235::24410064::INSTR'.
        timeout_ms: how long to wait for a reply before giving up.
        """
        rm = pyvisa.ResourceManager()
        if resource is None:
            resource = cls._find(rm)
        inst = rm.open_resource(resource)
        inst.timeout = timeout_ms
        # The scope's replies do NOT end in a newline; they end when the USB
        # message ends. Telling pyvisa to wait for a newline would hang, so we
        # leave read_termination off and only add a newline to commands we send.
        inst.read_termination = None
        inst.write_termination = "\n"
        # Waveform downloads are big; allow large USB chunks.
        try:
            inst.chunk_size = max(getattr(inst, "chunk_size", 0), 1 << 20)
        except Exception:
            pass
        # Clear any half-finished transfer left over from a previous program.
        try:
            inst.clear()
        except Exception:
            pass
        return cls(inst, rm)

    @staticmethod
    def _find(rm):
        """Look through the connected instruments for the scope's USB id."""
        for pattern in USB_PATTERNS:
            try:
                found = rm.list_resources(pattern)
            except Exception:
                found = ()
            if found:
                return found[0]
        raise RuntimeError(
            "DOS1104 not found. Check that the scope USB mode is USBTMC "
            "(Utility > Function > Configure > Device > USBTMC), the cable is in "
            "the right-side USB-Device port, and a VISA runtime is installed.\n"
            "Visible instruments: " + str(list(rm.list_resources()))
        )

    def close(self):
        """Close the connection. Always do this when finished."""
        try:
            self.inst.close()
        finally:
            if self._rm is not None:
                self._rm.close()

    # Let you use 'with DOS1104.connect() as scope:'
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------ basic talk
    def idn(self):
        """Return the scope's name/model/serial/firmware string."""
        return _clean(self.inst.query("*IDN?"))

    def ask(self, command):
        """Send any command that expects a reply, and return the cleaned text."""
        return _clean(self.inst.query(command))

    def send(self, command):
        """Send a command that does not expect a reply."""
        self.inst.write(command)

    # ---------------------------------------------------------- measurements
    def measure(self, channel, kind="vpp"):
        """
        Read one measurement from the scope, e.g. measure(1, "vpp").

        kind can be any key in MEASUREMENTS: vpp, vamp, vtop, vbase, freq,
        period, rtime, pwidth, nwidth, pduty, nduty, overshoot, preshoot.
        Returns a number (volts, seconds, hertz or percent) or None if the
        scope cannot measure it right now (for example, no signal).
        """
        self._check_channel(channel)
        word = MEASUREMENTS.get(kind.lower())
        if word is None:
            raise ValueError("unknown measurement '%s'. Options: %s"
                             % (kind, ", ".join(MEASUREMENTS)))
        return _to_number(self.inst.query(":MEAS:CH%d:%s?" % (channel, word)))

    def channel_scale(self, channel):
        """Return the channel's vertical scale in volts per division."""
        self._check_channel(channel)
        return _to_number(self.inst.query(":CH%d:SCAL?" % channel))

    def timebase(self):
        """Return the horizontal scale in seconds per division."""
        return _to_number(self.inst.query(":HORIzontal:Scale?"))

    def stats(self, channel):
        """
        Return a full set of statistics for a channel, as a dictionary.

        Vmax, Vmin, Vpp, Vmean and Vrms are computed here from the downloaded
        waveform (the firmware does not provide those four). The rest come
        straight from the scope. Handy to validate a signal in one call.
        """
        self._check_channel(channel)
        result = {}
        # First the firmware measurements (these are single quick questions).
        for kind in ("vamp", "vtop", "vbase", "freq", "period", "rtime",
                     "pwidth", "nwidth", "pduty", "nduty",
                     "overshoot", "preshoot"):
            try:
                result[kind] = self.measure(channel, kind)
            except Exception:
                result[kind] = None
        # Then download the wave and compute the level stats from it.
        wave = self.capture(channel)
        v = wave["volts"]
        result["vmax"] = float(v.max())
        result["vmin"] = float(v.min())
        result["vpp"] = float(v.max() - v.min())
        result["vmean"] = float(v.mean())
        result["vrms"] = float(np.sqrt(np.mean(v * v)))
        result["points"] = int(v.size)
        result["samplerate"] = wave["samplerate"]
        return result

    # ------------------------------------------------------------- waveforms
    def capture(self, channel):
        """
        Download the on-screen waveform of one channel (about 1500 points).

        Returns a dictionary:
          time        - numpy array of time in seconds
          volts       - numpy array of voltage (already calibrated)
          raw         - numpy array of the raw ADC codes
          volts_per_div, samplerate, dt, header (extra info from the scope)
        """
        self._check_channel(channel)
        head, raw = self._download(":DATA:WAVE:SCREEN:HEAD?",
                                   ":DATA:WAVE:SCREEN:CH%d?" % channel)
        return self._build_wave(head, raw, channel)

    def capture_deep(self, channel):
        """
        Download the deep-memory waveform (many more points than the screen,
        e.g. 5000+). Slower, but better for detailed analysis. Same dictionary
        shape as capture().
        """
        self._check_channel(channel)
        head, raw = self._download(":DATA:WAVE:DEPMEM:HEAD?",
                                   ":DATA:WAVE:DEPMEM:CH%d?" % channel)
        return self._build_wave(head, raw, channel)

    def screenshot(self, path):
        """
        Save a picture of the scope screen to a .bmp file. Note: this does not
        work on every firmware - if it times out, just skip it.
        """
        old = self.inst.timeout
        self.inst.timeout = max(old, 15000)
        try:
            self.inst.write(":DATA:WAVE:SCREEN:BMP?")
            raw = self.inst.read_raw()
        except Exception:
            self._recover()
            raise
        finally:
            self.inst.timeout = old
        start = raw.find(b"BM")            # a BMP file starts with "BM"
        with open(path, "wb") as f:
            f.write(raw[start:] if start >= 0 else raw[4:])
        return path

    # ------------------------------------------------------------ run control
    def run(self):
        """Start continuous acquisition."""
        self.inst.write(":RUNning RUN")

    def stop(self):
        """Stop acquisition (freeze the screen)."""
        self.inst.write(":RUNning STOP")

    def autoset(self):
        """Auto-scale to the input signal (like pressing Autoset)."""
        self.inst.write(":AUTOset on")

    def self_correct(self):
        """Run the scope's internal self-calibration."""
        self.inst.write(":SelfCorrect on")

    # ------------------------------------------------------------- internals
    def _download(self, head_cmd, data_cmd):
        """
        Ask for the header (text describing the capture) and the sample bytes.
        Both come as: 4 bytes saying how long the payload is, then the payload.
        If anything goes wrong mid-transfer we clear the link so the next call
        is not left out of sync.
        """
        try:
            head_text = self._read_block(head_cmd).decode("latin1")
            sample_bytes = self._read_block(data_cmd)
        except Exception:
            self._recover()
            raise
        return json.loads(head_text), sample_bytes

    def _read_block(self, command):
        """Send a command and read back a [4-byte length][payload] block."""
        self.inst.write(command)
        raw = self.inst.read_raw()
        length = int.from_bytes(raw[:4], "little")
        return raw[4:4 + length]

    def _build_wave(self, head, sample_bytes, channel):
        """Turn the raw header + bytes into the result dictionary."""
        codes = np.frombuffer(sample_bytes, dtype="<i2")   # 16-bit, little-endian
        samplerate = self._samplerate(head)
        dt = 1.0 / samplerate if samplerate else 0.0
        volts_per_div = self._channel_scale_from_head(head, channel)
        return {
            "time": np.arange(codes.size) * dt,
            "volts": codes.astype(float) * volts_per_div / CODES_PER_DIV,
            "raw": codes,
            "volts_per_div": volts_per_div,
            "samplerate": samplerate,
            "dt": dt,
            "header": head,
        }

    def _recover(self):
        """Try to reset the USB link after a failed transfer."""
        try:
            self.inst.clear()
        except Exception:
            pass

    @staticmethod
    def _samplerate(head):
        """Read the sample rate out of the header text, e.g. '(25KS/s)'."""
        text = head.get("SAMPLE", {}).get("SAMPLERATE", "")
        match = re.search(r"([0-9.]+)\s*([kKmMgG]?)S/s", text)
        if not match:
            return 0.0
        prefix = {"": 1, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6, "g": 1e9, "G": 1e9}
        return float(match.group(1)) * prefix[match.group(2)]

    @staticmethod
    def _channel_scale_from_head(head, channel):
        """Find this channel's volts-per-division inside the header."""
        for ch in head.get("CHANNEL", []):
            if ch.get("NAME") == "CH%d" % channel:
                return _to_number(ch.get("SCALE", "0V")) or 0.0
        return 0.0

    @staticmethod
    def _check_channel(channel):
        if channel not in (1, 2, 3, 4):
            raise ValueError("channel must be 1, 2, 3 or 4")


# Demo: run this file directly with  python dos1104.py
if __name__ == "__main__":
    with DOS1104.connect() as scope:
        print("Connected to:", scope.idn())
        print("CH1 peak-to-peak:", scope.measure(1, "vpp"), "V")
