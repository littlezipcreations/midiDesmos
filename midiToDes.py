from mido import MidiFile

def midi_note_to_freq(note):
	return round(440.0 * 2 ** ((note - 69) / 12), 2)

def midi_velocity_to_gain(velocity):
	return round(velocity / 127, 2)  # normalize 0-127 to 0-1

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

def midi_to_desmos_variable_slots_gain(filename, num_voices=4, minimal_fraction=0.25):
	"""
	Converts MIDI to Desmos arrays with notes N_Y and volume V_Y.
	Returns: (note_arrays, volume_arrays, ms_per_slot)
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

	voices_notes = [[] for _ in range(num_voices)]
	voices_volume = [[] for _ in range(num_voices)]
	active_notes = []  # currently sounding notes: (freq, remaining_slots, gain)
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
					freq, rem_slots, gain = active_notes[i]
					voices_notes[i].append(freq)
					voices_volume[i].append(gain)
					active_notes[i] = (freq, rem_slots - 1, gain)
				else:
					voices_notes[i].append(-1)
					voices_volume[i].append(0)
			# remove notes whose duration has expired
			active_notes = [n for n in active_notes if n[1] > 0]

		# Add new note
		if msg.type == 'note_on' and msg.velocity > 0:
			freq = midi_note_to_freq(msg.note)
			gain = midi_velocity_to_gain(msg.velocity)
			duration_ticks = msg.time if msg.time > 0 else 1
			slots = max(1, round(duration_ticks / ticks_per_slot))
			active_notes.append((freq, slots, gain))
		elif msg.type == 'note_off':
			freq = midi_note_to_freq(msg.note)
			active_notes = [n for n in active_notes if n[0] != freq]

	# Fill remaining slots to equal length
	max_len = max(len(v) for v in voices_notes)
	for v in voices_notes:
		while len(v) < max_len:
			v.append(-1)
	for v in voices_volume:
		while len(v) < max_len:
			v.append(0)

	# Convert to Desmos arrays
	desmos_note_arrays = [f"N_{i+1}=[" + ",".join(str(round(f,2)) for f in voices_notes[i]) + "]" for i in range(num_voices)]
	desmos_volume_arrays = [f"V_{i+1}=[" + ",".join(str(round(v,2)) for v in voices_volume[i]) + "]" for i in range(num_voices)]

	return desmos_note_arrays, desmos_volume_arrays, ms_per_slot

# -------------------------
# Example usage
midi_file = "midmid.mid"  # replace with your MIDI file
notes_arrays, volume_arrays, ms_value = midi_to_desmos_variable_slots_gain(midi_file, num_voices=4, minimal_fraction=0.25)

print(f"Set your ticker interval to: {ms_value} ms per slot\n")
for arr in notes_arrays:
	print(arr)
for arr in volume_arrays:
	print(arr)
