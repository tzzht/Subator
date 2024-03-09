import downloader
import transcriber
import translator
import spliter
import aligner
import os
import argparse
import sys
import shutil

argparser = argparse.ArgumentParser(description="Download, transcribe, translate, split, and align the fragments")
argparser.add_argument("--url", help="The url of the youtube video", required=True)
argparser.add_argument("--save_dir", help="The dir to save the output", required=True)
argparser.add_argument("--api_key_path", help="The path to the api key file", required=True)
argparser.add_argument("--llm", help="The language model to use. [qwen, glm]", required=False, default="qwen")

args = argparser.parse_args()
url = args.url
save_dir = args.save_dir
api_key_path = args.api_key_path
llm = args.llm

# Download the video
print(f"Start downloading the video from {url}")
video_path, audio_path, resouces_dir = downloader.downloader(url, save_dir)
print()

# Transcribe the video
print(f"Transcribe the audio from {audio_path}")
transcriber.transcriber(audio_path, resouces_dir)
print()
print("Please check if the transcription is correct.")
input("Press Enter to continue...")

# Translate the video
sentences_file_path = os.path.join(resouces_dir, 'sentences.txt')
print(f"Translate the sentences from {sentences_file_path}")

prompt = '你是一名计算机架构专家'
with open(api_key_path, 'r') as f:
    api_key = f.read()
translator.translator(sentences_file_path, resouces_dir, api_key, prompt, llm)

print('Translation completed, please check if the translation is correct. \nSearch "Please check the response." in translator.log. Then modify potentially erroneous lines in ch.txt.')
input("Press Enter to continue...")

# Split the sentences
en_path = os.path.join(resouces_dir, 'sentences.txt')
ch_path = os.path.join(resouces_dir, 'sentences_translated.txt')
print(f"Split the sentences from {en_path} and {ch_path}")
spliter.spliter(en_path, ch_path, resouces_dir)

# Align the fragments
fragments_file_path = os.path.join(resouces_dir, 'fragments.json')
timestamps_file_path = os.path.join(resouces_dir, 'timestamps.json')
print(f"Align the fragments from {fragments_file_path} and {timestamps_file_path}")
aligner.aligner(fragments_file_path, timestamps_file_path, os.path.join(resouces_dir, '..'))

# Copy log files to resources_dir
shutil.copy('./transcriber.log', resouces_dir)
shutil.copy('./translator.log', resouces_dir)
shutil.copy('./spliter.log', resouces_dir)
shutil.copy('./aligner.log', resouces_dir)