# DOS1104 SCPI command reference

This is the list of SCPI commands the Hanmatek DOS1104 understands, recovered by
inspecting the official "DS Wave" PC software (an Owon program) plus testing on a
real DOS1104 (firmware V1.2.0). The DOS1104 uses the **Owon SDS1104** command
set, so this should apply to that family too.

Two important things about how the scope talks:

- **Every reply ends with `->`.** A query like `:CH1:SCAL?` answers `1.00V->`.
  Strip the `->` before using the value. Measurements also carry a label and
  units, e.g. `:MEAS:CH1:PKPK?` → `Vpp : 2.040V->`.
- **Waveform downloads are binary.** The reply is `[4 bytes = length][payload]`,
  little-endian length. For a `HEAD?` query the payload is JSON text; for a
  channel-data query the payload is the samples as 16-bit little-endian integers.

Legend: ✅ = tested and working on the DOS1104; ▫ = found in the software, not
individually verified here.

---

## General / system

| Command | What it does |
|---|---|
| `*IDN?` ✅ | Identify: returns `HANMATEK,DOS1104,<serial>,<firmware>`. |
| `:MODEL?` ▫ | Returns the model code. |
| `:SCPI:DISP?` ▫ | Query SCPI display info. |
| `:SCPION` ▫ | Enable SCPI mode. |
| `:BEEP` ▫ | Buzzer. |

---

## Run control

| Command | What it does |
|---|---|
| `:RUNning RUN` ✅ | Start continuous acquisition. |
| `:RUNning STOP` ✅ | Stop acquisition (freeze the screen). |
| `:AUTOset on` ▫ | Autoset — auto-scale to the input signal. |
| `:SelfCorrect on` ▫ | Run the scope's internal self-calibration. |

---

## Channels (vertical)

`<n>` is the channel number 1–4. Replies include units and `->`.

| Command | What it does |
|---|---|
| `:CH<n>:SCAL?` / `:CH<n>:SCAL <v>` ✅ | Volts per division. Query gives e.g. `1.00V`. |
| `:CH<n>:OFFS?` / `:CH<n>:OFFS <v>` ✅ | Vertical offset. |
| `:CH<n>:COUP?` / `:CH<n>:COUP <DC\|AC>` ✅ | Input coupling. |
| `:CH<n>:PROB?` / `:CH<n>:PROB <1X\|10X\|...>` ✅ | Probe attenuation. Set this to match your probe, or readings are wrong. |
| `:CH<n>:DISP?` / `:CH<n>:DISP <ON\|OFF>` ✅ | Show/hide the channel. |
| `:CH<n>:INVERSE <ON\|OFF>` ▫ | Invert the trace. |

---

## Horizontal (timebase)

| Command | What it does |
|---|---|
| `:HORIzontal:Scale?` / `:HORIzontal:Scale <t>` ▫ | Seconds per division. |
| `:HORIzontal:OFFSET?` / `:HORIzontal:OFFSET <t>` ▫ | Horizontal position. |

---

## Acquisition

| Command | What it does |
|---|---|
| `:ACQUire:Mode <mode>` ▫ | Acquire mode (e.g. SAMPle, average, peak). |
| `:ACQUIRE:DEPMEM <depth>` ▫ | Memory depth (e.g. `5K`). |
| `:ACQUire:average:num <n>` ▫ | Number of averages when in average mode. |

The current acquisition info also comes back inside the waveform `HEAD?` JSON
(`SAMPLE.SAMPLERATE`, `SAMPLE.DEPMEM`, `SAMPLE.DATALEN`, `SAMPLE.TYPE`).

---

## Measurements

Format: `:MEAS:CH<n>:<TYPE>?`. The reply is a labelled value, e.g.
`Vpp : 2.040V->`. If the scope cannot measure it right now the value is `?`
(e.g. frequency with no signal → `F :   ?->`).

| TYPE | Reply label | Meaning |
|---|---|---|
| `PKPK` ✅ | Vpp | Peak-to-peak voltage |
| `VAMP` ✅ | Va | Amplitude (top − base) |
| `VTOP` ✅ | Vt | Top (the flat high level) |
| `VBAS` ✅ | Vb | Base (the flat low level) |
| `FREQ` ✅ | F | Frequency |
| `PER` ✅ | T | Period |
| `RTIME` ✅ | RT | Rise time |
| `PWIDTH` ✅ | PW | Positive pulse width |
| `NWIDTH` ✅ | NW | Negative pulse width |
| `PDUTY` ✅ | +D | Positive duty cycle (%) |
| `NDUTY` ✅ | −D | Negative duty cycle (%) |
| `OVERSHOOT` ✅ | Os | Overshoot (%) |
| `PRESHOOT` ✅ | Ps | Preshoot (%) |

**Not available over SCPI:** `Vmax`, `Vmin`, `Vmean`, `Vrms`. The PC software
computes those itself from the downloaded waveform — so does this driver, in
`stats()`. (`Vmax = max sample`, `Vmin = min sample`, `Vpp = max − min`,
`Vmean = average`, `Vrms = root-mean-square`.)

---

## Waveform download

Each of these returns a binary block: `[4-byte little-endian length][payload]`.

**Screen view** (what is currently drawn, ~1500 points — fast):

| Command | Payload |
|---|---|
| `:DATA:WAVE:SCREEN:HEAD?` ✅ | JSON text with timebase, sample rate, per-channel scale/probe/offset, trigger info. |
| `:DATA:WAVE:SCREEN:CH<n>?` ✅ | The channel samples, 16-bit little-endian integers (ADC codes). |
| `:DATA:WAVE:SCREEN:BMP?` ▫ | A screenshot as a BMP image. (Times out on some firmware.) |

**Deep memory** (the full acquisition record, thousands of points — slower, more
detail):

| Command | Payload |
|---|---|
| `:DATA:WAVE:DEPMEM:HEAD?` ✅ | Same kind of JSON header as above. |
| `:DATA:WAVE:DEPMEM:CH<n>?` ✅ | Deep-memory samples, 16-bit little-endian. |
| `:DATA:WAVE:DEPMEM:All?` ▫ | All channels' deep memory at once. |

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

The DOS1104 uses a single-trigger command tree. (All ▫ — present in the software;
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
| `:SAVE:READ:HEAD?` ▫ | Header for a stored capture. |
| `:SAVE:READ:DATA <...>` ▫ | Read stored capture data. |
| `:FILE:Download <...>` ▫ | Download a file from the scope. |
| `:FILE:UPLoad <...>` ▫ | Upload a file to the scope. |

---

## FFT

| Command | What it does |
|---|---|
| `:FFT:ch <n>` ▫ | Choose the FFT source channel. |
| `:FFT:display <ON\|OFF>` ▫ | Show/hide the FFT. |

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
