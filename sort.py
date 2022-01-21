import argparse
from collections import OrderedDict
import hashlib
import json
import os
from pick import pick
import re
from zipfile import ZipFile

parser = argparse.ArgumentParser(description="Utility script for managing BeatSaber Custom songs.")
parser.add_argument("--downloads-dir", metavar="<downloads-folder>", type=str, default="/home/mesch/Downloads", help="Root directory of Downloads folder. Where songs are unzipped from.", dest="DOWNLOADS_DIR")
parser.add_argument("--songs-dir", metavar="<custom-songs-folder>", type=str, default="/home/mesch/programming/song-sorter/songs", help="Root directory of Custom Songs Folder. Where songs will be searched for and added to.", dest="SONGS_DIR")
parser.add_argument("--playlists-dir", metavar="<playlists-folder>", type=str, default="/home/mesch/programming/song-sorter/playlists", help="Root directory of Song Playlists Folder. Uses rithik-b/PlaylistManager", dest="PLAYLISTS_DIR")
parser.add_argument("--no-unzip", action='store_true', help="If flag is set, do not attempt to unzip new songs from downloads folder into Custom Songs Folder.", dest="NO_UNZIP")
parser.add_argument("--no-sort", action='store_true', help="If flag is set, do not prompt user to add unsorted songs to playlists.", dest="NO_SORT")
parser.add_argument("--play-song", action='store_true', help="If flag is set, play songs suring playlist selection.", dest="PLAY_SONG")
args = parser.parse_args()
#TODO Add verbose

if args.PLAY_SONG:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    from pygame import mixer

def getZippedSongs():
    zipped_songs = []
    for root, dirs, files in os.walk(args.DOWNLOADS_DIR):
        for zip_file in [os.path.join(root, f) for f in files if f.endswith('.zip')]:
            with ZipFile(zip_file, 'r') as zf:
                if re.search("info.dat", " ".join(zf.namelist()), flags=re.IGNORECASE):
                    zipped_songs.append(zip_file)

    return zipped_songs

def getPlaylists():
    playlists = []
    for root, dirs, files in os.walk(args.PLAYLISTS_DIR):
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
    song_info = {}
    for song_dir in [e for e in os.scandir(args.SONGS_DIR) if e.is_dir()]:
        reg = re.search("info.dat", " ".join(os.listdir(song_dir)), flags=re.IGNORECASE)
        if reg:
            song_info_path = os.path.join(song_dir.path, reg.group(0))
            with open(song_info_path, encoding="utf8") as f:
                song_data = json.load(f, object_pairs_hook=OrderedDict)
                song_hash = generateSongHash(song_info_path, song_data)
                song_info[song_hash.upper()] = {"SongName": song_data["_songName"],
                                                "ArtistName": song_data["_songAuthorName"],
                                                "SongFile": os.path.join(song_dir.path, song_data["_songFilename"])}
    
    return song_info

def addSongToPlaylist(song_name, song_hash, playlist_file):
    with open(playlist_file, 'r+', encoding="utf8") as f:
        playlist_data = json.load(f)
        
        playlist_data["songs"].append({'songName': song_name, 'hash': song_hash})
        f.seek(0)
        f.write(json.dumps(playlist_data, indent=4))
        f.truncate()

def unzipNewSongs():
    zipped = getZippedSongs()
    for zip_file in zipped:
        unzip_loc = os.path.join(args.SONGS_DIR, os.path.splitext(os.path.basename(zip_file))[0])
        if not os.path.exists(unzip_loc):        
            with ZipFile(zip_file, 'r') as zf:
                zf.extractall(unzip_loc)
            os.remove(zip_file)

def promptAddUnsortedToPlaylist(play_audio):
    hashed = getHashedSongs()
    songs = getSongInfo()
    for s_hash,s_info in songs.items():
        if s_hash not in hashed:
            if play_audio:
                mixer.music.load(s_info['SongFile'])
                mixer.music.play()
            selection_title = f"Song '{s_info['SongName']}' by '{s_info['ArtistName']}' not in any playlist.\nAdd '{s_info['SongName']}' to playlist:"
            selection_options = (["SKIP"] + [os.path.splitext(os.path.relpath(p, args.PLAYLISTS_DIR))[0] for p in getPlaylists()])
            selection, idx = pick(selection_options, selection_title, indicator="-->")
            if selection != "SKIP":
                addSongToPlaylist(s_info["SongName"], s_hash, getPlaylists()[idx-1])
            if play_audio:
                mixer.music.stop()
                mixer.music.unload()

if not args.NO_UNZIP:
    print("Unzipping new Songs")
    unzipNewSongs()

if not args.NO_SORT:
    print("Sorting existing Songs")
    if args.PLAY_SONG:
        mixer.init()
    promptAddUnsortedToPlaylist(args.PLAY_SONG)