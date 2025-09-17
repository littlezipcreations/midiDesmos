from mido import MidiFile

def midi_note_to_freq(note):
    return round(440.0 * 2 ** ((note - 69) / 12), 2)

def calculate_ms_per_slot(mid, minimal_fraction=0.5):
    """
    Calculates ticker interval based on tempo and minimal fraction (e.g., semiquaver = 0.25)
    """
    tempo = 500000  # default tempo (120 BPM)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break
        if tempo != 500000:
            break
    ms_per_slot = (tempo / 1000) * minimal_fraction
    return round(ms_per_slot, 2)

def midi_to_desmos_variable_slots(filename, num_voices=4, minimal_fraction=0.25):
    """
    Converts MIDI to fixed-number, pitch-sorted Desmos arrays with variable note durations.
    - minimal_fraction: smallest fraction of a beat (e.g., 0.25 = semiquaver)
    Returns: (desmos_arrays, ms_per_slot)
    """
    mid = MidiFile(filename)
    ticks_per_beat = mid.ticks_per_beat
    ms_per_slot = calculate_ms_per_slot(mid, minimal_fraction)

    # Collect note events with absolute time
    events = []
    for track in mid.tracks:
        abs_time = 0
        for msg in track:
            abs_time += msg.time
            if msg.type in ['note_on', 'note_off']:
                events.append((abs_time, msg))
    events.sort(key=lambda x: x[0])

    voices = [[] for _ in range(num_voices)]
    active_notes = []  # currently sounding notes: (freq, remaining_slots)
    last_time = 0
    ticks_per_slot = ticks_per_beat * minimal_fraction

    for abs_time, msg in events:
        delta_time = abs_time - last_time
        slots_to_fill = round(delta_time / ticks_per_slot)
        last_time = abs_time

        # Fill voices for elapsed time
        for _ in range(slots_to_fill):
            active_notes.sort(key=lambda x: x[0], reverse=True)  # highest pitch first
            for i in range(num_voices):
                if i < len(active_notes):
                    voices[i].append(active_notes[i][0])
                    # decrement remaining slots
                    active_notes[i] = (active_notes[i][0], active_notes[i][1] - 1)
                else:
                    voices[i].append(-1)
            # remove notes whose duration has expired
            active_notes = [n for n in active_notes if n[1] > 0]

        # Add new note
        if msg.type == 'note_on' and msg.velocity > 0:
            freq = midi_note_to_freq(msg.note)
            # Determine duration in slots
            duration_ticks = msg.time if msg.time > 0 else 1
            slots = max(1, round(duration_ticks / ticks_per_slot))
            active_notes.append((freq, slots))
        elif msg.type == 'note_off':
            freq = midi_note_to_freq(msg.note)
            # remove any active notes matching this freq
            active_notes = [n for n in active_notes if n[0] != freq]

    # Fill remaining slots to equal length
    max_len = max(len(v) for v in voices)
    for v in voices:
        while len(v) < max_len:
            v.append(-1)

    # Convert to Desmos arrays
    desmos_arrays = []
    for idx, v in enumerate(voices):
        desmos_arrays.append(f"N{idx+1}=[" + ",".join(str(round(f,2)) for f in v) + "]")

    return desmos_arrays, ms_per_slot

# -------------------------
# Example usage
midi_file = "midmid.mid"  # replace with your MIDI file
arrays, ms_value = midi_to_desmos_variable_slots(midi_file, num_voices=4, minimal_fraction=0.25)

print(f"Set your ticker interval to: {ms_value} ms per slot")
for arr in arrays:
    print(arr)
