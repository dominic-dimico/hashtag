#!/usr/bin/python

################################################################################
# Library for video and music ripping
################################################################################

import youtube_dl
import toolbelt.editors
import os, sys, re
import hashtag
import code
import importlib

from pprint import pprint as pp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



################################################################################
# Required for parsing YouTube URLs
################################################################################
#importlib.reload(sys)
#sys.setdefaultencoding('utf-8')



################################################################################
# Need developer keys
################################################################################
DEVELOPER_KEY = 'AIzaSyCCRGfFmh-STKDORtAkfRAO3LZO9r42-5k'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'



################################################################################
# Search YouTube by keyword for videos
################################################################################
def youtube_search(query, num_results):

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
      developerKey=DEVELOPER_KEY)

    #code.interact(local=locals());

    search_response = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=num_results
    ).execute()

    videos = []
    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
          videos.append(
            (
             search_result['id']['videoId'],
             search_result['snippet']['title']
            )
          )

    return videos;



################################################################################
# Download all videos by URL
################################################################################
def download_vids(urls):
    ydl_opts = {
       "outtmpl": "%(id)s.%(ext)s",
       "continue_dl": True,
       "ratelimit": "250000",
       "ignoreerrors": True,
       "nooverwrites": True,
       "no_check_certificate": True,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
         ydl.download(urls);



################################################################################
# Take in strings (presumably from file) describing songs, and generate rows
# to append to database file
################################################################################
def songs2rows(songs):
    songrows = [];
    for song in songs:
        parts = song.split(";");
        path  = parts[0];
        tags  = [];
        if len(parts)>1: 
           tags = parts[1:];
        songpart = path.split("/");
        songrow = [
          path + ".mp3",
          "genre="  + songpart[0],
          "artist=" + songpart[1],
          "title="  + songpart[2],
        ] + tags;
        songrows.append(songrow);
    return songrows;



################################################################################
# Utility functions for music files
################################################################################
def hyphenate(s):
    return re.sub("[ \t]+", "-", s);

def dehyphenate(s):
    return re.sub("[\-]+", " ", s);



################################################################################
# Download music
################################################################################
def download_music(database):

    for d in database:

        path = d["path"];
        query = dehyphenate(d["artist"][0]) + " " + dehyphenate(d["title"][0]);

        videos = youtube_search(query, 1);
        urls = video_urls(videos);

        ydl_opts = {
           "outtmpl": path,
           "continue_dl": True,
           "ratelimit": "250000",
           "ignoreerrors": True,
           "nooverwrites": True,
           "no_check_certificate": True,
           'format': 'bestaudio/best',
           'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
           }]
        }

        #code.interact(local=locals())
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
             ydl.download(urls);



################################################################################
# Get video URLs for download
################################################################################
def video_urls(videos):
    baseurl = "http://youtube.com/watch?v="
    urls = []
    for (id, title) in videos:
        urls.append( baseurl+id );
    return urls;




################################################################################
# Allow user to filter titles
################################################################################
def vim_select(videos):
    titles = [video[1] for video in videos];
    #"\n".join(titles);
    titles = toolbelt.editors.vim("\n".join(titles));
    newtitles = titles.split("\n");
    newvideos = [];
    for (id, title) in videos:
        if title in newtitles:
           newvideos.append((id, title));
    return newvideos;



################################################################################
# Filter out IDs of videos which have been downloaded or banned
################################################################################
def filter_excluded(videos, excluded_ids):
    potential_ids = [v[0] for v in videos]
    common_ids   = hashtag.intersect(excluded_ids, potential_ids);
    filtered_ids = hashtag.difference(potential_ids, common_ids);
    # Reconstruct the tuple list
    new_videos = [];
    for filtered_id in filtered_ids:
        for (video_id, title) in videos:
            if filtered_id == video_id:
               new_videos.append((filtered_id, title));
    return new_videos;



################################################################################
# Filter out videos which have been banned
################################################################################
def filter_by_file(videos, filename="/home/dominic/vid/downloaded/excluded.txt"):
    excluded_file = open(filename);
    excluded_ids = excluded_file.readlines();
    excluded_ids = [vid.strip() for vid in ids];
    return filter_excluded(videos, excluded_ids);



################################################################################
# Filter out videos that have already been downloaded
################################################################################
def filter_downloaded(videos, basedir="/home/dominic/vid/downloaded"):
    file_ids = []
    for (root, subdirs, files) in os.walk(basedir):
        for filename in files:
            file_ids.append(filename.split(".")[0]);
    return filter_excluded(videos, file_ids);
