from collections import OrderedDict
import hashlib
import json
import os
from pick import pick
import re

SONGS = "/home/mesch/programming/song-sorter/songs"
PLAYLISTS = "/home/mesch/programming/song-sorter/playlists"

def getPlaylists():
    playlists = []
    for root, dirs, files in os.walk(PLAYLISTS):
        playlists.extend([os.path.join(root, f) for f in files if f.endswith('.bplist')])
    return playlists

def getHashedSongs():
    hashed = set()
    for p in getPlaylists():
        with open(p, encoding="utf8") as f:
            playlist_data = json.load(f)
            for song_data in playlist_data.get("songs", []):
                if "hash" in song_data:
                    hashed.add(song_data["hash"])
    return hashed

def generateSongHash(info_file, song_data):
    with open(info_file, encoding="utf8") as f:
        hash_string = f.read()
    for difficulty in song_data["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"]:
        with open(os.path.join(os.path.dirname(info_file), difficulty["_beatmapFilename"]), encoding="utf8") as f:
            hash_string = "".join([hash_string, f.read()])
    return hashlib.sha1(hash_string.encode()).hexdigest()

def getSongInfo():
    song_list = {}
    for song_dir in [e for e in os.scandir(SONGS) if e.is_dir()]:
        reg = re.search("info.dat", " ".join(os.listdir(song_dir)), flags=re.IGNORECASE)
        if reg:
            song_info_path = os.path.join(song_dir.path, reg.group(0))
            with open(song_info_path, encoding="utf8") as f:
                song_data = json.load(f, object_pairs_hook=OrderedDict)
                song_hash = generateSongHash(song_info_path, song_data)
                song_list[song_hash.upper()] = song_data["_songName"]
    
    return song_list

def addSongToPlaylist(song_name, song_hash, playlist_file):
    with open(playlist_file, 'r+', encoding="utf8") as f:
        playlist_data = json.load(f)
        
        playlist_data["songs"].append({'songName': song_name, 'hash': song_hash})
        f.seek(0)
        f.write(json.dumps(playlist_data, indent=4))
        f.truncate()

hashed = getHashedSongs()
songs = getSongInfo()

for s_hash,s_title in songs.items():
    if s_hash not in hashed:
        selection_title = f"Song '{s_title}' not in any playlist.\nAdd '{s_title}' to playlist:"
        selection_options = (["SKIP"] + [os.path.splitext(os.path.relpath(p, PLAYLISTS))[0] for p in getPlaylists()])
        selection, idx = pick(selection_options, selection_title, indicator="-->")
        if selection != "SKIP":
            addSongToPlaylist(s_title, s_hash, getPlaylists()[idx-1])