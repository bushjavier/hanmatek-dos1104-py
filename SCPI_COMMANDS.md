# DOS1104 SCPI command reference

This is the list of SCPI commands the Hanmatek DOS1104 understands, recovered by
inspecting the official "DS Wave" PC software (an Owon program) plus testing on a
real DOS1104 (firmware V1.2.0). The DOS1104 uses the **Owon SDS1104** command
set, so this should apply to that family too.

Two important things about how the scope talks:

- **Every reply ends with `->`.** A query like `:CH1:SCAL?` answers `1.00V->`.
  Strip the `->` before using the value. Measurements also carry a label and
  units, e.g. `:MEAS:CH1:PKPK?` returns `Vpp : 2.040V->`.
- **Waveform downloads are binary.** The reply is `[4 bytes = length][payload]`,
  little-endian length. For a `HEAD?` query the payload is JSON text; for a
  channel-data query the payload is the samples as 16-bit little-endian integers.

Legend: `(tested)` = verified working on the DOS1104; (unverified) = found in the software, not
individually verified here.

---

## General / system

| Command | What it does |
|---|---|
| `*IDN?` (tested) | Identify: returns `HANMATEK,DOS1104,<serial>,<firmware>`. |
| `:MODEL?` (unverified) | Returns the model code. |
| `:SCPI:DISP?` (unverified) | Query SCPI display info. |
| `:SCPION` (unverified) | Enable SCPI mode. |
| `:BEEP` (unverified) | Buzzer. |

---

## Run control

| Command | What it does |
|---|---|
| `:RUNning RUN` (tested) | Start continuous acquisition. |
| `:RUNning STOP` (tested) | Stop acquisition (freeze the screen). |
| `:AUTOset on` (unverified) | Autoset - auto-scale to the input signal. |
| `:SelfCorrect on` (unverified) | Run the scope's internal self-calibration. |

---

## Channels (vertical)

`<n>` is the channel number 1-4. Replies include units and `->`.

| Command | What it does |
|---|---|
| `:CH<n>:SCAL?` / `:CH<n>:SCAL <v>` (tested) | Volts per division. Query gives e.g. `1.00V`. |
| `:CH<n>:OFFS?` / `:CH<n>:OFFS <v>` (tested) | Vertical offset. |
| `:CH<n>:COUP?` / `:CH<n>:COUP <DC\|AC>` (tested) | Input coupling. |
| `:CH<n>:PROB?` / `:CH<n>:PROB <1X\|10X\|...>` (tested) | Probe attenuation. Set this to match your probe, or readings are wrong. |
| `:CH<n>:DISP?` / `:CH<n>:DISP <ON\|OFF>` (tested) | Show/hide the channel. |
| `:CH<n>:INVERSE <ON\|OFF>` (unverified) | Invert the trace. |

---

## Horizontal (timebase)

| Command | What it does |
|---|---|
| `:HORIzontal:Scale?` / `:HORIzontal:Scale <t>` (unverified) | Seconds per division. |
| `:HORIzontal:OFFSET?` / `:HORIzontal:OFFSET <t>` (unverified) | Horizontal position. |

---

## Acquisition

| Command | What it does |
|---|---|
| `:ACQUire:Mode <mode>` (unverified) | Acquire mode (e.g. SAMPle, average, peak). |
| `:ACQUIRE:DEPMEM <depth>` (unverified) | Memory depth (e.g. `5K`). |
| `:ACQUire:average:num <n>` (unverified) | Number of averages when in average mode. |

The current acquisition info also comes back inside the waveform `HEAD?` JSON
(`SAMPLE.SAMPLERATE`, `SAMPLE.DEPMEM`, `SAMPLE.DATALEN`, `SAMPLE.TYPE`).

---

## Measurements

Format: `:MEAS:CH<n>:<TYPE>?`. The reply is a labelled value, e.g.
`Vpp : 2.040V->`. If the scope cannot measure it right now the value is `?`
(e.g. frequency with no signal: `F :   ?->`).

| TYPE | Reply label | Meaning |
|---|---|---|
| `PKPK` (tested) | Vpp | Peak-to-peak voltage |
| `VAMP` (tested) | Va | Amplitude (top - base) |
| `VTOP` (tested) | Vt | Top (the flat high level) |
| `VBAS` (tested) | Vb | Base (the flat low level) |
| `FREQ` (tested) | F | Frequency |
| `PER` (tested) | T | Period |
| `RTIME` (tested) | RT | Rise time |
| `PWIDTH` (tested) | PW | Positive pulse width |
| `NWIDTH` (tested) | NW | Negative pulse width |
| `PDUTY` (tested) | +D | Positive duty cycle (%) |
| `NDUTY` (tested) | -D | Negative duty cycle (%) |
| `OVERSHOOT` (tested) | Os | Overshoot (%) |
| `PRESHOOT` (tested) | Ps | Preshoot (%) |

**Not available over SCPI:** `Vmax`, `Vmin`, `Vmean`, `Vrms`. The PC software
computes those itself from the downloaded waveform - so does this driver, in
`stats()`. (`Vmax = max sample`, `Vmin = min sample`, `Vpp = max - min`,
`Vmean = average`, `Vrms = root-mean-square`.)

---

## Waveform download

Each of these returns a binary block: `[4-byte little-endian length][payload]`.

**Screen view** (what is currently drawn, ~1500 points - fast):

| Command | Payload |
|---|---|
| `:DATA:WAVE:SCREEN:HEAD?` (tested) | JSON text with timebase, sample rate, per-channel scale/probe/offset, trigger info. |
| `:DATA:WAVE:SCREEN:CH<n>?` (tested) | The channel samples, 16-bit little-endian integers (ADC codes). |
| `:DATA:WAVE:SCREEN:BMP?` (unverified) | A screenshot as a BMP image. (Times out on some firmware.) |

**Deep memory** (the full acquisition record, thousands of points - slower, more
detail):

| Command | Payload |
|---|---|
| `:DATA:WAVE:DEPMEM:HEAD?` (tested) | Same kind of JSON header as above. |
| `:DATA:WAVE:DEPMEM:CH<n>?` (tested) | Deep-memory samples, 16-bit little-endian. |
| `:DATA:WAVE:DEPMEM:All?` (unverified) | All channels' deep memory at once. |

To turn the 16-bit codes into volts:
`volts = code * volts_per_division / 6400` (see the header for each channel's
volts-per-division). 6400 codes = one vertical division; this is verified.

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

The DOS1104 uses a single-trigger command tree. (All of these are unverified - present in the software;
adjust to taste and verify on your unit.)

| Command | What it does |
|---|---|
| `:TRIGger:SINGle:MODE <mode>` / `?` | Trigger mode. |
| `:TRIGger:SINGle:SOURce CH<n>` | Trigger source channel. |
| `:TRIGger:SINGle:EDGE <RISE\|FALL>` | Edge slope. |
| `:TRIGger:SINGle:EDGE:SOURce?` | Query the edge source. |
| `:TRIGger:SINGle:EDGe:LEVel <v>` | Trigger level. |
| `:TRIGger:SINGle:COUPling <c>` | Trigger coupling. |
| `:TRIGger:SINGle:Sweep <AUTO\|NORMAL\|SINGLE>` | Sweep mode. |
| `:TRIGger:SINGle:HoldOff <t>` | Hold-off time. |
| `:TRIGger:SINGle:Slope <s>` | Slope settings (slope-trigger). |
| `:TRIGger:SINGle:Time <t>` | Time setting (pulse/time trigger). |
| `:TRIGger:SINGle:Sync <s>` | Sync (video trigger). |
| `:TRIGger:SINGle:LineNum <n>` | Video line number. |
| `:TRIGger:SINGle:polarity <p>` | Polarity (video/pulse). |
| `:TRIGger:SINGle:LLevel <v>` / `:ULevel <v>` | Lower / upper level (window trigger). |
| `:TRIGger:SINGle:SIGN <s>` | Sign / condition. |
| `:TRIGger:SINGle:System <s>` | Trigger system setting. |

---

## Files / save

| Command | What it does |
|---|---|
| `:SAVE:READ:HEAD?` (unverified) | Header for a stored capture. |
| `:SAVE:READ:DATA <...>` (unverified) | Read stored capture data. |
| `:FILE:Download <...>` (unverified) | Download a file from the scope. |
| `:FILE:UPLoad <...>` (unverified) | Upload a file to the scope. |

---

## FFT

| Command | What it does |
|---|---|
| `:FFT:ch <n>` (unverified) | Choose the FFT source channel. |
| `:FFT:display <ON\|OFF>` (unverified) | Show/hide the FFT. |

---

## Shared firmware: multimeter and signal generator

The DOS1104 firmware is shared across a product line that also includes a
multimeter and an arbitrary-waveform generator. These commands appear in the
software; they only do something on units that have that hardware.

**Multimeter (DMM):**
`:FUNC DCV|ACV|DCA|ACA|RES|CAP|DIOD|BEEP`, `:VOLT:DC`, `:VOLT:AC`,
`:CURR:DC`, `:CURR:AC`, `:RES`, `:DIOD`, `:RANG <range>`, `:REL`, `:UNIT <u>`,
`:READ?` (read the current measurement), `:STEP`.

**Built-in generator:**
`:function sine|square|ramp|pulse|arb`, `:function:freq <hz>`,
`:function:ampl <v>`, `:function:offset <v>`, `:function:high <v>`,
`:function:low <v>`, `:function:period <s>`, `:function:pulse:dtycycle <%>`,
`:function:ramp:symmetry <%>`, `:channel:CH1 <on/off>`, `:channel:CH2 <on/off>`.

---

*Found something this list gets wrong, or a command that behaves differently on
your scope? Please open an issue.*
