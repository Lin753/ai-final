import midi
import numpy as np
import mido

lowerBound = 24
upperBound = 102
span = upperBound-lowerBound


def midiToNoteStateMatrix(midifile, squash=True, span=span):
    mid = mido.MidiFile(midifile)

    timeleft = [track[0].time for track in mid.tracks]

    posns = [0 for _ in mid.tracks]

    statematrix = []
    time = 0

    state = [[0, 0] for _ in range(span)]
    statematrix.append(state)
    condition = True
    while condition:
        if time % (mid.ticks_per_beat / 4) == (mid.ticks_per_beat / 8):
            # Crossed a note boundary. Create a new state, defaulting to holding notes
            oldstate = state
            state = [[oldstate[x][0], 0] for x in range(span)]
            statematrix.append(state)
        for i in range(len(timeleft)):  # For each track
            if not condition:
                break
            while timeleft[i] == 0:
                track = mid.tracks[i]
                pos = posns[i]

                evt = track[pos]
                if isinstance(evt, mido.Message) and evt.type == 'note_on':
                    if (evt.note < lowerBound) or (evt.note >= upperBound):
                        pass
                    else:
                        if evt.velocity == 0:
                            state[evt.note - lowerBound] = [0, 0]
                        else:
                            state[evt.note - lowerBound] = [1, 1]
                try:
                    timeleft[i] = track[pos + 1].time
                    posns[i] += 1
                except IndexError:
                    timeleft[i] = None

            if timeleft[i] is not None:
                timeleft[i] -= 1

        if all(t is None for t in timeleft):
            break

        time += 1

    S = np.array(statematrix)
    statematrix = np.hstack((S[:, :, 0], S[:, :, 1]))
    statematrix = np.asarray(statematrix).tolist()
    return statematrix


def noteStateMatrixToMidi(statematrix, name="example", span=span):
    statematrix = np.array(statematrix)
    if not len(statematrix.shape) == 3:
        statematrix = np.dstack((statematrix[:, :span], statematrix[:, span:]))
    statematrix = np.asarray(statematrix)
    
    mid = mido.MidiFile(ticks_per_beat=960)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    span = upperBound - lowerBound
    tickscale = 55
    
    lastcmdtime = 0
    prevstate = [[0, 0] for _ in range(span)]
    for time, state in enumerate(statematrix + [prevstate[:]]):
        offNotes = []
        onNotes = []
        for i in range(span):
            n = state[i]
            p = prevstate[i]
            if p[0] == 1:
                if n[0] == 0:
                    offNotes.append(i)
                elif n[1] == 1:
                    offNotes.append(i)
                    onNotes.append(i)
            elif n[0] == 1:
                onNotes.append(i)
        for note in offNotes:
            track.append(mido.Message('note_off', note=note + lowerBound, velocity=0, time=(time - lastcmdtime) * tickscale))
            lastcmdtime = time
        for note in onNotes:
            track.append(mido.Message('note_on', note=note + lowerBound, velocity=40, time=(time - lastcmdtime) * tickscale))
            lastcmdtime = time
            
        prevstate = state
    
    track.append(mido.MetaMessage('end_of_track', time=1))

    mid.save("{}.mid".format(name))
