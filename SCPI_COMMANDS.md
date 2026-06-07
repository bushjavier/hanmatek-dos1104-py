# DOS1104 SCPI command reference

This is the list of SCPI commands the Hanmatek DOS1104 understands, recovered by
inspecting the official "DS Wave" PC software (an Owon program) and then tested
on a real DOS1104 (firmware V1.2.0) by driving it with a known signal from a
function generator. The DOS1104 uses the Owon SDS1104 command set, so this
should apply to that family too.

Status of each command:

- tested = verified working on the DOS1104 (firmware V1.2.0).
- A note in italics means it was not fully verified, with the reason.

Two things about how the scope talks:

- Every reply ends with `->`. A query like `:CH1:SCAL?` answers `1.00V->`.
  Strip the `->` before using the value. Measurements also carry a label and
  units, e.g. `:MEAS:CH1:PKPK?` returns `Vpp : 2.040V->`.
- Waveform downloads are binary. The reply is `[4 bytes = length][payload]`,
  little-endian length. For a `HEAD?` query the payload is JSON text; for a
  channel-data query the payload is the samples as 16-bit little-endian integers.

Use the keywords exactly as written below. Some accept the long form only, e.g.
`:HORIzontal:Scale?` works but the short `:HORI:SCAL?` returns nothing.

---

## General / system

| Command | Status | What it does |
|---|---|---|
| `*IDN?` | tested | Identify: returns `HANMATEK,DOS1104,<serial>,<firmware>`. |
| `:MODEL?` | tested | Returns the model code (e.g. `110410101`). |
| `:BEEP` | tested | Sounds the buzzer. |
| `:SCPION` | tested | Enable SCPI mode (accepted, no readback). |
| `:SCPI:DISP?` | *no reply on V1.2.0* | Query SCPI display info. |

---

## Run control

| Command | Status | What it does |
|---|---|---|
| `:RUNning RUN` | tested | Start continuous acquisition. |
| `:RUNning STOP` | tested | Stop acquisition (freeze the screen). |
| `:AUTOset on` | tested | Autoset - auto-scale to the input signal. *Note: the scope is busy for a few seconds afterwards; clear the link / wait before the next command or replies can get out of sync.* |
| `:SelfCorrect on` | *not exercised* | Runs the internal self-calibration (a long operation). |

Run state can be read with `:TRIG:STAT?` (returns `TRIG` when running, `STOP`
when stopped).

---

## Channels (vertical)

`<n>` is the channel number 1-4. Replies include units and `->`. All of these
were tested (query and set) on channel 1.

| Command | Status | What it does |
|---|---|---|
| `:CH<n>:SCAL?` / `:CH<n>:SCAL <v>` | tested | Volts per division. Query gives e.g. `1.00V`; set e.g. `:CH1:SCAL 500mV`. |
| `:CH<n>:OFFS?` / `:CH<n>:OFFS <v>` | tested | Vertical offset. Set e.g. `:CH1:OFFS 0.5V`. |
| `:CH<n>:COUP?` / `:CH<n>:COUP <DC\|AC>` | tested | Input coupling. |
| `:CH<n>:PROB?` / `:CH<n>:PROB <1X\|10X\|...>` | tested | Probe attenuation. Set this to match your probe, or readings are wrong. |
| `:CH<n>:DISP?` / `:CH<n>:DISP <ON\|OFF>` | tested | Show/hide the channel. |
| `:CH<n>:INVERSE <ON\|OFF>` | tested | Invert the trace (accepted; there is no query to read it back). |

---

## Horizontal (timebase)

| Command | Status | What it does |
|---|---|---|
| `:HORIzontal:Scale?` / `:HORIzontal:Scale <t>` | tested | Seconds per division. Query gives e.g. `500us`; set e.g. `:HORIzontal:Scale 200us`. |
| `:HORIzontal:OFFSET?` / `:HORIzontal:OFFSET <t>` | tested (query) | Horizontal position. *The query reads back; the exact set value/format was not pinned down.* |

---

## Acquisition

| Command | Status | What it does |
|---|---|---|
| `:ACQUire:Mode?` / `:ACQUire:Mode <SAMPle\|AVERage\|...>` | tested | Acquire mode. |
| `:ACQUire:average:num?` / `:ACQUire:average:num <n>` | tested (query) | Number of averages. *Setting it only takes effect while in AVERage mode.* |
| `:ACQUIRE:DEPMEM?` / `:ACQUIRE:DEPMEM <depth>` | tested (query) | Memory depth (e.g. `5K`). *Query reads back; only the model's allowed depth values are accepted on set.* |

The current acquisition info also comes back inside the waveform `HEAD?` JSON
(`SAMPLE.SAMPLERATE`, `SAMPLE.DEPMEM`, `SAMPLE.DATALEN`, `SAMPLE.TYPE`).

---

## Measurements

Format: `:MEAS:CH<n>:<TYPE>?`. The reply is a labelled value, e.g.
`Vpp : 2.040V->`. If the scope cannot measure it right now the value is `?`
(e.g. frequency with no signal: `F :   ?->`). All of these were tested.

| TYPE | Reply label | Meaning |
|---|---|---|
| `PKPK` | Vpp | Peak-to-peak voltage |
| `VAMP` | Va | Amplitude (top - base) |
| `VTOP` | Vt | Top (the flat high level) |
| `VBAS` | Vb | Base (the flat low level) |
| `FREQ` | F | Frequency |
| `PER` | T | Period |
| `RTIME` | RT | Rise time |
| `PWIDTH` | PW | Positive pulse width |
| `NWIDTH` | NW | Negative pulse width |
| `PDUTY` | +D | Positive duty cycle (%) |
| `NDUTY` | -D | Negative duty cycle (%) |
| `OVERSHOOT` | Os | Overshoot (%) |
| `PRESHOOT` | Ps | Preshoot (%) |

Not available over SCPI: `Vmax`, `Vmin`, `Vmean`, `Vrms`. The PC software
computes those from the downloaded waveform - so does this driver, in `stats()`.
(`Vmax = max sample`, `Vmin = min sample`, `Vpp = max - min`,
`Vmean = average`, `Vrms = root-mean-square`.)

---

## Waveform download

Each returns a binary block: `[4-byte little-endian length][payload]`. All tested.

Screen view (what is currently drawn, ~1500 points, fast):

| Command | Status | Payload |
|---|---|---|
| `:DATA:WAVE:SCREEN:HEAD?` | tested | JSON with timebase, sample rate, per-channel scale/probe/offset, trigger info. |
| `:DATA:WAVE:SCREEN:CH<n>?` | tested | Channel samples, 16-bit little-endian integers (ADC codes). |
| `:DATA:WAVE:SCREEN:BMP?` | tested | A screenshot image. *Needs a long timeout (~15 s).* |

Deep memory (the full acquisition record, thousands of points, slower):

| Command | Status | Payload |
|---|---|---|
| `:DATA:WAVE:DEPMEM:HEAD?` | tested | Same kind of JSON header. |
| `:DATA:WAVE:DEPMEM:CH<n>?` | tested | Deep-memory samples, 16-bit little-endian. |
| `:DATA:WAVE:DEPMEM:All?` | tested | All channels' deep memory in one block. |

To turn the 16-bit codes into volts:
`volts = code * volts_per_division / 6400` (the per-channel volts-per-division is
in the header). 6400 codes = one vertical division; this is verified.

Example `HEAD?` JSON (trimmed):

```json
{
  "TIMEBASE": { "SCALE": "10ms", "HOFFSET": 0 },
  "SAMPLE":   { "DATALEN": 1520, "SAMPLERATE": "(25KS/s)", "TYPE": "SAMPle", "DEPMEM": "5K" },
  "CHANNEL":  [ { "NAME": "CH1", "SCALE": "1.00V", "PROBE": "10X",
                  "COUPLING": "DC", "OFFSET": -195, "DISPLAY": "ON" } ],
  "IDN": "HANMATEK,DOS1104,24410064,V1.2.0"
}
```

---

## Trigger

Single-trigger command tree. `:MODE?`, `:SOURce` and `:EDGE:SOURce?` were tested
(e.g. setting `:TRIGger:SINGle:SOURce CH2` then reading `:EDGE:SOURce?` returns
`CH2`). The other entries are part of the same working tree but were not each
read back individually.

| Command | Status | What it does |
|---|---|---|
| `:TRIGger:SINGle:MODE?` / `:TRIGger:SINGle:MODE <mode>` | tested | Trigger mode (returns e.g. `EDGE`). |
| `:TRIGger:SINGle:SOURce CH<n>` | tested | Trigger source channel. |
| `:TRIGger:SINGle:EDGE:SOURce?` | tested | Read the edge source. |
| `:TRIGger:SINGle:EDGE <RISE\|FALL>` | *set only* | Edge slope. |
| `:TRIGger:SINGle:EDGe:LEVel <v>` | *set only* | Trigger level. |
| `:TRIGger:SINGle:COUPling <c>` | *set only* | Trigger coupling. |
| `:TRIGger:SINGle:Sweep <AUTO\|NORMAL\|SINGLE>` | *set only* | Sweep mode. |
| `:TRIGger:SINGle:HoldOff <t>` | *set only* | Hold-off time. |
| `:TRIGger:SINGle:Slope <s>` | *set only* | Slope-trigger settings. |
| `:TRIGger:SINGle:Time <t>` | *set only* | Time setting (pulse/time trigger). |
| `:TRIGger:SINGle:Sync <s>` | *set only* | Sync (video trigger). |
| `:TRIGger:SINGle:LineNum <n>` | *set only* | Video line number. |
| `:TRIGger:SINGle:polarity <p>` | *set only* | Polarity (video/pulse). |
| `:TRIGger:SINGle:LLevel <v>` / `:ULevel <v>` | *set only* | Lower / upper level (window trigger). |
| `:TRIGger:SINGle:SIGN <s>` | *set only* | Sign / condition. |
| `:TRIGger:SINGle:System <s>` | *set only* | Trigger system setting. |

---

## Saved captures (internal memory)

These read a capture stored in the scope's internal memory - no USB stick
needed.

| Command | Status | What it does |
|---|---|---|
| `:SAVE:READ:HEAD?` | tested | JSON header of the stored capture (sample rate, scales, length, etc.). |
| `:SAVE:READ:DATA` | tested | The stored samples as a binary block (e.g. 10000 bytes = 5000 points x 2). |

---

## File transfer

| Command | Status | What it does |
|---|---|---|
| `:FILE:Download <...>` | *not exercised* | Transfer a file from the scope. Needs a filename argument and a binary payload; the sub-protocol was not reverse-engineered. |
| `:FILE:UPLoad <...>` | *not exercised* | Transfer a file to the scope (same caveat). |

You do not need these for measurements or waveform capture - those all work over
USB directly, and saved captures come back through `:SAVE:READ:*` above.

---

## FFT

| Command | Status | What it does |
|---|---|---|
| `:FFT:display <ON\|OFF>` | *set accepted; query empty on V1.2.0* | Show/hide the FFT. |
| `:FFT:ch <n>` | *set only* | Choose the FFT source channel. |

---

## Not present on the DOS1104

The firmware is shared with a product line that also has a multimeter and a
built-in signal generator. The DOS1104 has neither, so these commands return
nothing on it. They are listed only for reference and for other models in the
family.

Multimeter: `:FUNC DCV|ACV|DCA|ACA|RES|CAP|DIOD|BEEP`, `:VOLT:DC`, `:VOLT:AC`,
`:CURR:DC`, `:CURR:AC`, `:RES`, `:DIOD`, `:RANG <range>`, `:REL`, `:UNIT <u>`,
`:READ?`, `:STEP`.

Generator: `:function sine|square|ramp|pulse|arb`, `:function:freq <hz>`,
`:function:ampl <v>`, `:function:offset <v>`, `:function:high <v>`,
`:function:low <v>`, `:function:period <s>`, `:function:pulse:dtycycle <%>`,
`:function:ramp:symmetry <%>`, `:channel:CH1 <on/off>`, `:channel:CH2 <on/off>`.

---

*Found something this list gets wrong, or a command that behaves differently on
your scope? Please open an issue.*
