#!/usr/bin/python

import youtube_dl
import toolbelt
import os
import sys
import re
import hashtag
import code
import importlib
import configparser

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from hashtag.hashtag import HashTagger



class YouTubeRipper():


    ################################################################################
    # Need developer keys
    ################################################################################

    def __init__(self, 
       hashtagdbfile="/home/dominic/mus/database.tag", 
       configfile="/home/dominic/.config/hashtag/ripper.cfg",
    ):
        self.ht = HashTagger(hashtagdbfile);
        config = configparser.ConfigParser();
        config.read(configfile);
        self.developer_key       = config['youtube']['developer_key']
        self.yt_api_service_name = 'youtube'
        self.yt_api_version      = 'v3'
        self.youtube = build(self.yt_api_service_name, 
                             self.yt_api_version,
                             developerKey=self.developer_key)



    ################################################################################
    # Search YouTube by keyword for videos
    ################################################################################
    def youtube_search(self, query, num_results):
        search_response = self.youtube.search().list(
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
    def download_vids(self, urls):
        ydl_opts = {
           "outtmpl"              : "youtube_%(id)s.%(ext)s",
           "continue_dl"          : True,
           "ratelimit"            : "250000",
           "ignoreerrors"         : True,
           "nooverwrites"         : True,
           "no_check_certificate" : True,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
             ydl.download(urls);



    ################################################################################
    # Take in strings (presumably from file) describing songs, and generate rows
    # to append to database file
    ################################################################################
    def songs2rows(self, songs):
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
    def hyphenate(self, s):
        return re.sub("[ \t]+", "-", s);

    def dehyphenate(self, s):
        return re.sub("[\-]+", " ", s);



    ################################################################################
    # Download music
    ################################################################################
    def download_music(self, database):
        for d in database:
            path     = d["path"];
            query    = (self.dehyphenate(d["artist"][0]) + " " + 
                        self.dehyphenate(d["title"][0]));
            videos   =  self.youtube_search(query, 1);
            urls     =  self.video_urls(videos);
            ydl_opts = {
               "outtmpl"              : path,
               "continue_dl"          : True,
               "ratelimit"            : "250000",
               "ignoreerrors"         : True,
               "nooverwrites"         : True,
               "no_check_certificate" : True,
               'format'               : 'bestaudio/best',
               'postprocessors'       : [{
                    'key'              : 'FFmpegExtractAudio',
                    'preferredcodec'   : 'mp3',
                    'preferredquality' : '192',
               }]
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                 ydl.download(urls);



    ################################################################################
    # Get video URLs for download
    ################################################################################
    def video_urls(self, videos):
        baseurl = "http://youtube.com/watch?v="
        urls = []
        for (id, title) in videos:
            urls.append( baseurl+id );
        return urls;




    ################################################################################
    # Allow user to filter titles
    ################################################################################
    def vim_select(self, videos):
        titles = [video[1] for video in videos];
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
    def filter_excluded(self, videos, excluded_ids):
        potential_ids = [v[0] for v in videos]
        common_ids    = self.ht.intersect(excluded_ids, potential_ids);
        filtered_ids  = self.ht.difference(potential_ids, common_ids);
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
    def filter_by_file(self, videos, filename="/home/dominic/vid/downloaded/excluded.txt"):
        excluded_file = open(filename);
        excluded_ids = excluded_file.readlines();
        excluded_ids = [vid.strip() for vid in ids];
        return self.filter_excluded(videos, excluded_ids);



    ################################################################################
    # Filter out videos that have already been downloaded
    ################################################################################
    def filter_downloaded(self, videos, basedir="/home/dominic/vid/downloaded"):
        file_ids = []
        for (root, subdirs, files) in os.walk(basedir):
            for filename in files:
                file_ids.append(filename.split(".")[0]);
        return self.filter_excluded(videos, file_ids);


    def music(self, songs):
        if isinstance(songs, str):
           songs = [songs];
        songrows  = self.songs2rows(songs);
        musicdb = self.ht.parserows(songrows);
        self.download_music(musicdb);
        self.ht.append_entries(songrows);


    def vids(self, query, maxResults=20):
        videos = self.youtube_search(
          query,
          maxResults
        );
        videos = self.filter_downloaded(videos);
        videos = self.vim_select(videos);
        self.download_vids(
          self.video_urls(videos)
        )
