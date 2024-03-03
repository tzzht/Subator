import downloader
import transcriber
import translator
import spliter
import aligner
import os
import argparse
import sys

argparser = argparse.ArgumentParser(description="Download, transcribe, translate, split, and align the content")
argparser.add_argument("--url", help="The url of the youtube video", required=True)
argparser.add_argument("--save_dir", help="The dir to save the output", required=True)
argparser.add_argument("--model_path", help="The path to the model file", required=True)
argparser.add_argument("--api_key_path", help="The path to the api key file", required=True)
argparser.add_argument("--llm", help="The language model to use. [qwen, glm]", required=False, default="qwen")

args = argparser.parse_args()
url = args.url
save_dir = args.save_dir
model_path = args.model_path
api_key_path = args.api_key_path
llm = args.llm


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

print("Transcription completed, please check if the transcription is correct. \nPress Enter to continue...", file=sys.stderr)
input("Press Enter to continue...")

# Translate the video
print(f"Translate the content from {resouces_dir}/audio.txt", file=sys.stderr)
content_path = os.path.join(resouces_dir, 'audio.txt')

prompt = '你是一名芯片专家'
with open(api_key_path, 'r') as f:
    api_key = f.read()
translator.translator(content_path, resouces_dir, api_key, prompt, llm)

print('Translation completed, please check if the translation is correct. \nSearch "Please check the response." in subator.log. Then modify potentially erroneous lines in ch.txt. \nPress Enter to continue...', file=sys.stderr)
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

print(f"Subtitles are saved to {save_dir}.", file=sys.stderr)