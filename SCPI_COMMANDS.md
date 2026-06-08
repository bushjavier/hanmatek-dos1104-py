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

(`:SCPION` and `:SCPI:DISP?` look like system commands but are not - they belong
to the multimeter, see the "Not present" section at the end.)

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

`<n>` is the channel number 1-4. Replies include units and `->`. These were
tested (query and set). Waveform capture works on all four channels; a
measurement returns a value on any channel whose display is ON.

| Command | Status | What it does |
|---|---|---|
| `:CH<n>:SCAL?` / `:CH<n>:SCAL <v>` | tested | Volts per division. Query gives e.g. `1.00V`; set e.g. `:CH1:SCAL 500mV`. |
| `:CH<n>:OFFS?` / `:CH<n>:OFFS <v>` | tested | Vertical offset. Set e.g. `:CH1:OFFS 0.5V`. |
| `:CH<n>:COUP?` / `:CH<n>:COUP <DC\|AC>` | tested | Input coupling. |
| `:CH<n>:PROB?` / `:CH<n>:PROB <1X\|10X\|...>` | tested | Probe attenuation. Set this to match your probe, or readings are wrong. |
| `:CH<n>:DISP?` / `:CH<n>:DISP <ON\|OFF>` | tested | Show/hide the channel. |
| `:CH<n>:INVERSE <ON\|OFF>` | tested | Flip the trace vertically (multiply the channel by -1). Useful to compare against another channel or to undo a probe inversion. The scope accepts it but offers no query to read the state back. |

---

## Horizontal (timebase)

| Command | Status | What it does |
|---|---|---|
| `:HORIzontal:Scale?` / `:HORIzontal:Scale <t>` | tested | Seconds per division. Query gives e.g. `500us`; set e.g. `:HORIzontal:Scale 200us`. |
| `:HORIzontal:OFFSET?` / `:HORIzontal:OFFSET <t>` | tested | Horizontal position. Query and set both work (e.g. `:HORIzontal:OFFSET 500us`). |

---

## Acquisition

| Command | Status | What it does |
|---|---|---|
| `:ACQUire:Mode?` / `:ACQUire:Mode <SAMPle\|AVERage\|...>` | tested | Acquire mode. |
| `:ACQUire:average:num?` / `:ACQUire:average:num <n>` | tested | Number of averages. Set takes effect while in AVERage mode (verified 4 -> 16). |
| `:ACQUIRE:DEPMEM?` / `:ACQUIRE:DEPMEM <depth>` | tested (query) | Memory depth (e.g. `5K`). *Query reads back; setting it had no effect on V1.2.0 - the depth appears fixed/auto.* |

The current acquisition info also comes back inside the waveform `HEAD?` JSON
(`SAMPLE.SAMPLERATE`, `SAMPLE.DEPMEM`, `SAMPLE.DATALEN`, `SAMPLE.TYPE`).

---

## Measurements

Format: `:MEAS:CH<n>:<TYPE>?`. The reply is a labelled value, e.g.
`Vpp : 2.040V->`. If the scope cannot measure it right now the value is `?`
(e.g. frequency with no signal: `F :   ?->`). All of these were tested.

| TYPE | Reply label | Meaning |
|---|---|---|
| `MAX` | Ma | Maximum voltage |
| `MIN` | Mi | Minimum voltage |
| `PKPK` | Vpp | Peak-to-peak voltage |
| `VAMP` | Va | Amplitude (top - base) |
| `VTOP` | Vt | Top (the flat high level) |
| `VBAS` | Vb | Base (the flat low level) |
| `AVER` | V | Average (mean) voltage |
| `CYCRMS` | TR | RMS over one cycle |
| `FREQ` | F | Frequency |
| `PER` | T | Period |
| `RTIME` | RT | Rise time |
| `PWIDTH` | PW | Positive pulse width |
| `NWIDTH` | NW | Negative pulse width |
| `PDUTY` | +D | Positive duty cycle (%) |
| `NDUTY` | -D | Negative duty cycle (%) |
| `OVERSHOOT` | Os | Overshoot (%) |
| `PRESHOOT` | Ps | Preshoot (%) |

The scope computes max/min/mean/rms itself - note the SCPI words are
`MAX`/`MIN`/`AVER`/`CYCRMS`, not the obvious `VMAX`/`VMIN`/`VAVG`/`VRMS` (those
return nothing). The driver's `stats()` reads all of these straight from the
scope.

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
`CH2`). The rest are marked *set only*: the scope accepts them and acts on them,
but there is no query (`?`) form to read the value back over SCPI, so they cannot
be auto-verified. Descriptions below explain what each one controls.

| Command | Status | What it does |
|---|---|---|
| `:TRIGger:SINGle:MODE?` / `:TRIGger:SINGle:MODE <mode>` | tested | The trigger type: EDGE, pulse, video, slope, etc. Query returns e.g. `EDGE`. |
| `:TRIGger:SINGle:SOURce CH<n>` | tested | Which input channel the trigger watches. |
| `:TRIGger:SINGle:EDGE:SOURce?` | tested | Reads back the edge-trigger source channel. |
| `:TRIGger:SINGle:EDGE <RISE\|FALL>` | *set only* | For edge trigger: fire on the rising edge or the falling edge. |
| `:TRIGger:SINGle:EDGe:LEVel <v>` | *set only* | The voltage threshold the signal must cross to trigger. |
| `:TRIGger:SINGle:COUPling <c>` | *set only* | How the trigger path is filtered before the comparator (DC, AC, HF-reject, LF-reject, noise-reject). |
| `:TRIGger:SINGle:Sweep <AUTO\|NORMAL\|SINGLE>` | *set only* | When the scope draws: AUTO = free-run if no trigger arrives; NORMAL = only when a trigger occurs; SINGLE = capture one trigger then stop. |
| `:TRIGger:SINGle:HoldOff <t>` | *set only* | Dead time after a trigger during which new triggers are ignored - helps lock onto repetitive but complex waveforms. |
| `:TRIGger:SINGle:Slope <s>` | *set only* | Settings for the slope trigger (fire on a rate of change rather than a level). |
| `:TRIGger:SINGle:Time <t>` | *set only* | The time/width threshold for pulse-width and timeout triggers. |
| `:TRIGger:SINGle:Sync <s>` | *set only* | Video trigger sync type (line/field) for TV-style signals. |
| `:TRIGger:SINGle:LineNum <n>` | *set only* | Which video line to trigger on (video trigger). |
| `:TRIGger:SINGle:polarity <p>` | *set only* | Pulse/video polarity: positive-going or negative-going. |
| `:TRIGger:SINGle:LLevel <v>` / `:ULevel <v>` | *set only* | Lower and upper thresholds for the window trigger (fire when the signal enters/leaves the band between them). |
| `:TRIGger:SINGle:SIGN <s>` | *set only* | The comparison for the pulse-width trigger (wider than / narrower than / inside a range). |
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

The FFT view shows the frequency spectrum (the math transform) of a channel.
Both commands are accepted but there is no working query on V1.2.0, so the state
cannot be read back over SCPI.

| Command | Status | What it does |
|---|---|---|
| `:FFT:display <ON\|OFF>` | *set accepted; query empty on V1.2.0* | Turn the FFT (spectrum) view on or off. |
| `:FFT:ch <n>` | *set only* | Choose which input channel the FFT is computed from. |

---

## Not present on the DOS1104

The firmware is shared with a product line that also has a multimeter and a
built-in signal generator. The DOS1104 has neither, so these commands return
nothing on it. They are listed only for reference and for other models in the
family.

Multimeter: `:FUNC DCV|ACV|DCA|ACA|RES|CAP|DIOD|BEEP`, `:VOLT:DC`, `:VOLT:AC`,
`:CURR:DC`, `:CURR:AC`, `:RES`, `:DIOD`, `:RANG <range>`, `:REL`, `:UNIT <u>`,
`:READ?`, `:STEP`, `:SCPION`, `:SCPI:DISP?`.

(`:SCPION` and `:SCPI:DISP?` look like general SCPI commands but they are
multimeter commands - in the software they are handled by the "SCPI MultiMeter"
class, `SCPIMMAction` / `ScpiMMFrm`. On the DOS1104 they return nothing. Verified:
`:SCPION` then `:SCPI:DISP?`, plus `:SCPI:DISPlay?` and `:DISPlay?`, all reply
empty.)

Generator: `:function sine|square|ramp|pulse|arb`, `:function:freq <hz>`,
`:function:ampl <v>`, `:function:offset <v>`, `:function:high <v>`,
`:function:low <v>`, `:function:period <s>`, `:function:pulse:dtycycle <%>`,
`:function:ramp:symmetry <%>`, `:channel:CH1 <on/off>`, `:channel:CH2 <on/off>`.

---

*Found something this list gets wrong, or a command that behaves differently on
your scope? Please open an issue.*
