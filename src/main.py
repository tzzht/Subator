import downloader
import transcriber
import translator
import spliter
import aligner
import os
import argparse
import sys
def check_contents(content_path, MAX_LINE_LENGTH):
    # Read the file
    if not os.path.exists(content_path):
        print(f"File '{content_path}' not found.")
        exit(1)
    with open(content_path, 'r', encoding='utf-8') as f:
        all_contents = f.readlines()
    # strip the contents
    all_contents = [i.strip() for i in all_contents]
    # check the length of the contents
    for i, content in enumerate(all_contents):
        if len(content) > MAX_LINE_LENGTH*3:
            print(f"Line {i+1} is too long: {len(content)}")
            print(content)
            print("")

argparser = argparse.ArgumentParser(description="Download, transcribe, translate, split, and align the content")
argparser.add_argument("--url", help="The url of the youtube video", required=True)
argparser.add_argument("--save_dir", help="The dir to save the output", required=True)
argparser.add_argument("--model_path", help="The path to the model file", required=True)
argparser.add_argument("--api_key_path", help="The path to the api key file", required=True)

args = argparser.parse_args()
url = args.url
save_dir = args.save_dir
model_path = args.model_path
api_key_path = args.api_key_path


print(f"Start downloading the video from {url}", file=sys.stderr)
# Get the video info
yt = downloader.get_video_info(url)

# Get the directory to save the outputs, the directory is save_dir/video_author/video_title
video_author = ''.join(e for e in yt.author if e.isalnum())
video_title = ''.join(e for e in yt.title if e.isalnum())
save_dir = os.path.join(save_dir, video_author, video_title)
resouces_dir = os.path.join(save_dir, "resources")

# Download the streams
print(f"Save the resources to {resouces_dir}")
# get the streams, filter the video and audio streams
# the video streams are filtered by the type="video", mime_type="video/webm", res="1080p", progressive=False
# the audio streams are filtered by the type="audio", mime_type="audio/webm", abr="160kbps"
streams = yt.streams
video_streams = streams.filter(type="video", mime_type="video/webm", res="1080p", progressive=False)
audio_streams = streams.filter(type="audio", mime_type="audio/webm", abr="160kbps")
# if the video or audio streams are not found, print the error message
if len(video_streams) == 0:
    print("Video stream is not found, please input the itag of the video stream", file=sys.stderr)
    itag = int(input("Please input the itag of the video stream: "))
    video_stream = streams.get_by_itag(itag)
else:
    video_stream = video_streams[0]

if len(audio_streams) == 0:
    print("Audio stream is not found, please input the itag of the audio stream", file=sys.stderr)
    itag = int(input("Please input the itag of the audio stream: "))
    audio_stream = streams.get_by_itag(itag)
else:
    audio_stream = audio_streams[0]

# download the video and audio streams
video_path = downloader.downloader(resouces_dir, video_stream)
audio_path = downloader.downloader(resouces_dir, audio_stream)

# Transcribe the video
print(f"Transcribe the audio from {audio_path}", file=sys.stderr)
transcriber.transcriber(audio_path, resouces_dir, model_path)

print("Transcription completed, please check if the transcription is correct. Press Enter to continue...", file=sys.stderr)
input("Press Enter to continue...")

# Translate the video
print(f"Translate the content from {resouces_dir}/audio.txt", file=sys.stderr)
content_path = os.path.join(resouces_dir, 'audio.txt')
MAX_LINE_LENGTH = 80
# Check the contents
check_contents(content_path, MAX_LINE_LENGTH)
print("Please check the contents and manually split the long lines if needed. Press Enter to continue...", file=sys.stderr)
input("Press Enter to continue...")

prompt = '你是一名PC装机专家'
with open(api_key_path, 'r') as f:
    api_key = f.read()
translator.translator(content_path, resouces_dir, api_key, prompt)

print("Translation completed, please check if the translation is correct. Press Enter to continue...", file=sys.stderr)
input("Press Enter to continue...")

# Split the content
print(f"Split the content from {resouces_dir}/en.txt and {resouces_dir}/ch.txt", file=sys.stderr)
en_path = os.path.join(resouces_dir, 'en.txt')
ch_path = os.path.join(resouces_dir, 'ch.txt')
spliter.spliter(en_path, ch_path, resouces_dir, True)

# Align the content
print(f"Align the content from {resouces_dir}/audio.json, {resouces_dir}/en_splited.txt, and {resouces_dir}/ch_splited.txt", file=sys.stderr)
json_file_path = os.path.join(resouces_dir, 'audio.json')
splited_en_path = os.path.join(resouces_dir, 'en_splited.txt')
splited_ch_path = os.path.join(resouces_dir, 'ch_splited.txt')
aligner.aligner(json_file_path, splited_en_path, splited_ch_path, save_dir)