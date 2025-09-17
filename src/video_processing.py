
from moviepy import *
import librosa
import crepe
import numpy as np
import pandas as pd
from scipy.signal import medfilt
import matplotlib.pyplot as plt
from pathlib import Path
import mido
import os

def video_note_split(vName, threshold=0.8, tune_thresh=0.3, dur_thresh=0.1,
                     find_eyes=True, show_notes=False):
    """
    vName: string ending with .mp4 that contains the video with the notes
    creates a csv file containing the starting and ending of all notes
    """

    video = VideoFileClip(vName)
    audio = video.audio
    h, w = video.size
    fps = video.fps
    print('video size ', w, 'x', h, ', at ', fps, ' fps.')
    t = audio.duration
    sr = audio.fps
    print('audio duration: ', t, ', sampling rate: ', sr)
    print(audio)
    y = audio.to_soundarray(fps=sr)

    y = librosa.core.to_mono(np.transpose(y))

    time, frequency, confidence, activation = crepe.predict(y, sr, viterbi=True)
    mfr = medfilt(frequency, 21)
    midi = 69 + 12 * np.log2(mfr / 440)
    mcon = medfilt(confidence, 21)

    if show_notes:
        plt.plot(time, midi)
        plt.plot(time, np.min(midi) + mcon * (np.max(midi) - np.min(midi)))
        plt.show()

    registeringNote = False
    notas = {
        'midi': [],
        'inicio': [],
        'fim': [],
        'duracao': [],
        'i': [],
        'j': [],
        'avg conf': [],
        'std dev': [],
        'median freq': [],   # Hz
        'avg midi': []       # valor médio contínuo em MIDI
    }
    notas = pd.DataFrame(notas)

    for i in range(time.shape[0]):
        if confidence[i] > threshold:
            if not registeringNote:
                registeringNote = True
                row = pd.DataFrame({'midi': [midi[i]], 'inicio': [time[i]], 'i': [i]})
                notas.loc[len(notas)] = row.iloc[0]
        else:
            if registeringNote:
                registeringNote = False
                notas.at[notas.index[-1], 'j'] = i
                notas.at[notas.index[-1], 'fim'] = time[i]
                notas.at[notas.index[-1], 'duracao'] = (
                    notas.at[notas.index[-1], 'fim'] -
                    notas.at[notas.index[-1], 'inicio']
                )

                i0 = int(notas.at[notas.index[-1], 'i'])
                j0 = i
                notas.at[notas.index[-1], 'avg conf'] = np.average(confidence[i0:j0])
                notas.at[notas.index[-1], 'median freq'] = np.median(frequency[i0:j0])
                notas.at[notas.index[-1], 'avg midi'] = np.average(midi[i0:j0])

    # remove notas curtas demais
    indexLowDur = notas[notas['duracao'] < dur_thresh].index
    notas = notas.drop(indexLowDur, inplace=False)

    # remove notas desafinadas
    for index, row in notas.iterrows():
        i = int(notas.at[index, 'i'])
        j = int(notas.at[index, 'j'])
        note = int(round(np.average(midi[i:j])))
        std = np.sqrt(np.average(abs(midi[i:j] - note) ** 2))
        notesThatPassed = np.abs(midi[i:j] - note) < tune_thresh
        if not all(notesThatPassed):
            notas = notas.drop(index, inplace=False)
        else:
            notas.at[index, 'midi'] = note
            notas.at[index, 'std dev'] = std

    print("identified notes: ")
    print(notas)

    vName = vName.split('.')[0]
    notas.to_csv(vName + '.csv', index=False)
    return vName + '.csv'
    return notas



def folder_note_split(instrument_name ,threshold=0.8, tune_thresh=0.3,dur_thresh=0.1):
    """
    folder: string containig a folder that contains .mp4 files
    """
    folder=Path('instruments')/Path(instrument_name)

    videos=[video_path for video_path in folder.iterdir() if video_path.exists() and video_path.suffix=='.mp4']
    print(videos)
    df_list=[]
    for vid in videos:
        dfcsv = video_note_split(str(vid), threshold, tune_thresh, dur_thresh)
        df_list.append(dfcsv)
    df=pd.concat(df_list, keys=videos,names=[folder, 'Notes'])
    df = df.sort_values(by='midi')

    df.to_csv(Path(folder)/Path(instrument_name+'.csv'))
    df=df.reset_index(level=[folder])
    return df



def midi_to_dict(midi_path, channel=None):
    """
    Lê um arquivo MIDI e retorna dict com listas:
    {
      "midi": [...],
      "start": [...],
      "end": [...],
      "velocity": [...],
      "channel": [...]
    }
    
    Args:
        midi_path (str): Caminho do arquivo MIDI.
        channel (int or None): Canal MIDI a filtrar (0-15). 
                               Se None, pega todos os canais.
    """
    mid = mido.MidiFile(midi_path)
    
    notes = []
    ongoing_notes = {}  # chave = (nota, canal), valor = (start_time, velocity)
    time = 0.0
    
    for msg in mid:  # percorre eventos já mesclados
        time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            if channel is None or msg.channel == channel:
                ongoing_notes[(msg.note, msg.channel)] = (time, msg.velocity)
        elif msg.type in ("note_off", "note_on") and msg.velocity == 0:
            if channel is None or msg.channel == channel:
                key = (msg.note, msg.channel)
                if key in ongoing_notes:
                    start_time, vel = ongoing_notes.pop(key)
                    notes.append({
                        "midi": msg.note,
                        "start": start_time,
                        "end": time,
                        "velocity": vel,
                        "channel": msg.channel
                    })
    
    # organiza como dict de listas
    result = {
        "midi": [],
        "start": [],
        "end": [],
        "velocity": [],
        "channel": []
    }
    for n in sorted(notes, key=lambda x: x["start"]):
        for k in result.keys():
            result[k].append(n[k])
    
    return result


def count_channels(midi):
    for k in midi:
        print(k,midi[k])
    print()
    return len(set(midi["channel"]))
