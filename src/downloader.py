from pytube import YouTube
import argparse
import os

def get_video_info(url):
    yt = YouTube(url)
    # print the statistics
    print(f"Video Title: {yt.title}")
    print(f"Video Author: {yt.author}")
    print(f"Video Description: {yt.description}")
    print(f"Video Length: {yt.length} seconds")
    print(f"Publish Date: {yt.publish_date}")
    print(f"Video Rating: {yt.rating}")
    print(f"Video Views: {yt.views}")
    for stream in yt.streams:
        print(stream)
    return yt

def downloader(save_dir, stream):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    print(stream)

    file_name = f"{stream.type}.{stream.mime_type.split('/')[1]}"
    print(file_name)
    save_path = os.path.join(save_dir, file_name)
    print(f"Save the stream to {save_path}")
    # If the file already exists, skip the download
    if not os.path.exists(save_path):
        print(f"Downloading the stream to {save_path}")
        stream.download(save_dir, filename=file_name)
    else:
        print(f"Stream already exists at {save_path}")
    return save_path
    
if __name__ == "__main__":
    # parse the arguments, url and save_path
    parser = argparse.ArgumentParser(description="Download the youtube video")
    parser.add_argument("--url", help="The url of the youtube video", required=True)
    parser.add_argument("--save_dir", help="The dir to save the downloaded video", required=True)
    args = parser.parse_args()
    url = args.url
    save_dir = args.save_dir

    # get the video info
    yt = get_video_info(url)
    # get the directory to save the video, the directory is save_dir/video_author/video_title
    video_author = ''.join(e for e in yt.author if e.isalnum())
    video_title = ''.join(e for e in yt.title if e.isalnum())
    save_dir = os.path.join(save_dir, video_author, video_title, "resources")
    print(f"Save the resources to {save_dir}")
    # get the streams, filter the video and audio streams
    # the video streams are filtered by the type="video", mime_type="video/webm", res="1080p", progressive=False
    # the audio streams are filtered by the type="audio", mime_type="audio/webm", abr="160kbps"
    streams = yt.streams
    video_streams = streams.filter(type="video", mime_type="video/webm", res="1080p", progressive=False)
    audio_streams = streams.filter(type="audio", mime_type="audio/webm", abr="160kbps")
    # if the video or audio streams are not found, print the error message
    if len(video_streams) == 0:
        print("Video stream is not found")
    if len(audio_streams) == 0:
        print("Audio stream is not found")
    # download the video and audio streams
    downloader(save_dir, video_streams[0])
    downloader(save_dir, audio_streams[0])