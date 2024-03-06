import downloader
import transcriber
import translator
import spliter
import aligner
import os
import argparse
import sys

argparser = argparse.ArgumentParser(description="Download, transcribe, translate, split, and align the fragments")
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

# Download the video
print(f"Start downloading the video from {url}")
video_path, audio_path, resouces_dir = downloader.downloader(url, save_dir)

# Transcribe the video
print(f"Transcribe the audio from {audio_path}")
transcriber.transcriber(audio_path, resouces_dir, model_path)

print("Transcription completed, please check if the transcription is correct.")
input("Press Enter to continue...")

# Translate the video
print(f"Translate the sentences from {resouces_dir}/audio.txt")
sentences_file_path = os.path.join(resouces_dir, 'audio.txt')

prompt = '你是一名全栈工程师'
with open(api_key_path, 'r') as f:
    api_key = f.read()
translator.translator(sentences_file_path, resouces_dir, api_key, prompt, llm)

print('Translation completed, please check if the translation is correct. \nSearch "Please check the response." in translator.log. Then modify potentially erroneous lines in ch.txt.')
input("Press Enter to continue...")

# Split the sentences
print(f"Split the sentences from {resouces_dir}/en.txt and {resouces_dir}/ch.txt")
en_path = os.path.join(resouces_dir, 'en.txt')
ch_path = os.path.join(resouces_dir, 'ch.txt')
spliter.spliter(en_path, ch_path, resouces_dir)

# Align the fragments
print(f"Align the fragments from {resouces_dir}/audio.json, {resouces_dir}/en_splited.txt, and {resouces_dir}/ch_splited.txt")
json_file_path = os.path.join(resouces_dir, 'audio.json')
splited_en_path = os.path.join(resouces_dir, 'en_splited.txt')
splited_ch_path = os.path.join(resouces_dir, 'ch_splited.txt')
aligner.aligner(json_file_path, splited_en_path, splited_ch_path, os.path.join(resouces_dir, '..'))

# Copy log files to resources_dir
os.system(f"cp ./translator.log {resouces_dir}")
os.system(f"cp ./spliter.log {resouces_dir}")
os.system(f"cp ./aligner.log {resouces_dir}")
