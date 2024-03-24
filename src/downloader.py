from pytube import YouTube
import argparse
import os
import sys
import subator_constants

def get_video_info(url):
    yt = YouTube(url)
    # print the statistics
    print(f"Video Title: {yt.title}")
    print(f"Video Author: {yt.author}")
    # print(f"Video Description: {yt.description}")
    print(f"Video Length: {yt.length} seconds")
    print(f"Publish Date: {yt.publish_date}")
    print(f"Video Rating: {yt.rating}")
    print(f"Video Views: {yt.views}")
    for stream in yt.streams:
        print(f'    {stream}')
    print()
    return yt

def download_stream(save_dir, stream):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        print(f"Create the directory {save_dir}")

    file_name = f"{stream.type}.{stream.mime_type.split('/')[1]}"
    save_path = os.path.join(save_dir, file_name)

    # If the file already exists, skip the download
    if not os.path.exists(save_path):
        print(f"Downloading the stream to {save_path}")
        stream.download(save_dir, filename=file_name)
    else:
        print(f"Stream already exists at {save_path}")
    return save_path

def downloader(url, save_dir):
    # Get the video info
    yt = get_video_info(url)

    # Get the directory to save the outputs, the directory is save_dir/video_author/video_title
    video_author = ''.join(e for e in yt.author if e.isalnum())
    video_title = ''.join(e for e in yt.title if e.isalnum())
    resouces_dir = os.path.join(save_dir, video_author, video_title, "resources")

    # Get the streams, filter the video and audio streams
    streams = yt.streams
    video_streams = streams.filter(type="video", mime_type=f"{subator_constants.VIDEO_MIME_TYPE}", res=f"{subator_constants.VIDEO_RES}", progressive=subator_constants.VIDEO_PROGRESSIVE)
    audio_streams = streams.filter(type="audio", mime_type=f"{subator_constants.AUDIO_MIME_TYPE}", abr=f"{subator_constants.AUDIO_ABR}")

    # if the video or audio streams are not found, print the error message
    if len(video_streams) == 0:
        # print("Video stream is not found, please input the itag of the video stream")
        # itag = int(input("Please input the itag of the video stream: "))
        # video_stream = streams.get_by_itag(itag)
        # Find the video stream with the highest resolution
        video_stream = streams.order_by("resolution").last()
    else:
        video_stream = video_streams[0]

    if len(audio_streams) == 0:
        # print("Audio stream is not found, please input the itag of the audio stream")
        # itag = int(input("Please input the itag of the audio stream: "))
        audio_stream = streams.order_by("abr").last()
    else:
        audio_stream = audio_streams[0]

    # Download the video and audio streams
    video_path = download_stream(resouces_dir, video_stream)
    audio_path = download_stream(resouces_dir, audio_stream)

    print("Download completed")
    return video_path, audio_path, resouces_dir

    
if __name__ == "__main__":
    # parse the arguments, url and save_path
    parser = argparse.ArgumentParser(description="Download the youtube video")
    parser.add_argument("--url", help="The url of the youtube video", required=True)
    parser.add_argument("--save_dir", help="The dir to save the downloaded video", required=True)
    args = parser.parse_args()
    url = args.url
    save_dir = args.save_dir

    # download the video
    downloader(url, save_dir)
   