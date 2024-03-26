import json
import os
import argparse
import srt
from datetime import timedelta
import sys
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"{__name__}.log", mode="w", encoding="utf-8")
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
    

def eliminate_end_puncuation(text):
    if len(text) > 0 and text[-1] in ',.':
        return text[:-1]
    return text

def check_clean_words(words1, words2):
    logger.info('Checking clean words...')
    if len(words1) != len(words2):
        logger.error(f'Cheking clean words failed: Lengths are not equal: {len(words1)} != {len(words2)}')
        # exit(1)
    for i in range(len(words1)):
        logger.debug(f'Checking clean words: {words1[i]} == {words2[i]}')
        if eliminate_end_puncuation(words1[i]) != eliminate_end_puncuation(words2[i]):
            logger.error(f'Cheking clean words failed: Words are not equal: {words1[i]} != {words2[i]}')
            exit(1)
    logger.info('Cheking clean words passed: All words are equal')

def aligner(fragments_file_path, timestamps_file_path, output_dir):
    # Load the json file
    if not os.path.exists(fragments_file_path):
        logger.error(f"File '{fragments_file_path}' not found.")
        exit(1)
    if not os.path.exists(timestamps_file_path):
        logger.error(f"File '{timestamps_file_path}' not found.")
        exit(1)
    with open(fragments_file_path, 'r', encoding='utf-8') as f:
        fragments = json.load(f)
    with open(timestamps_file_path, 'r', encoding='utf-8') as f:
        timestamps = json.load(f)

    words1 = []
    words2 = []
    for fragment in fragments:
        for sentence in fragment['en']:
            words1.extend(sentence.split())
    
    for timestamp in timestamps:
        words2.append(timestamp['word'])
    check_clean_words(words1, words2)
  
    fragments_with_timestamps = []
    i = 0
    for fragment in fragments:
        fragment_with_timestamps = {}
        fragment_with_timestamps['en'] = fragment['en']
        fragment_with_timestamps['ch'] = fragment['ch']
        fragment_with_timestamps['en_start'] = []
        fragment_with_timestamps['en_end'] = []
        fragment_with_timestamps['ch_start'] = ''
        fragment_with_timestamps['ch_end'] = ''

        for sentence in fragment['en']:
            clean_words = [eliminate_end_puncuation(word) for word in sentence.split()]
            en_start = timestamps[i]['start']
            en_end = timestamps[i+len(clean_words)-1]['end']
            fragment_with_timestamps['en_start'].append(en_start)
            fragment_with_timestamps['en_end'].append(en_end)
            i += len(clean_words)
        assert len(fragment_with_timestamps['en_start']) == len(fragment_with_timestamps['en_end'])
        fragment_with_timestamps['ch_start'] = fragment_with_timestamps['en_start'][0]
        fragment_with_timestamps['ch_end'] = fragment_with_timestamps['en_end'][-1]
        fragments_with_timestamps.append(fragment_with_timestamps)
    
    assert i == len(timestamps)

    # Create en subtitles
    en_subtitles = []
    subtitle_index = 1
    for fragment in fragments_with_timestamps:
        for j, sentence in enumerate(fragment['en']):
            en_subtitles.append(srt.Subtitle(index=subtitle_index+j, content=sentence, start=timedelta(seconds=fragment['en_start'][j]), end=timedelta(seconds=fragment['en_end'][j])))
        subtitle_index += len(fragment['en'])

    # Create ch subtitles
    ch_subtitles = []
    for i, fragment in enumerate(fragments_with_timestamps):
        ch_subtitles.append(srt.Subtitle(index=i+1, content=fragment['ch'], start=timedelta(seconds=fragment['ch_start']), end=timedelta(seconds=fragment['ch_end'])))
   
    logger.info("Subtitles are created")

    # Write the subtitles to the output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(os.path.join(output_dir, "en.srt"), 'w', encoding='utf-8') as f:
        f.write(srt.compose(en_subtitles))

    with open(os.path.join(output_dir, "ch.srt"), 'w', encoding='utf-8') as f:
        f.write(srt.compose(ch_subtitles))

    logger.info(f"Subtitles are saved to {output_dir}")


if __name__ == "__main__":
    # Parse the arguments
    parser = argparse.ArgumentParser(description='Align the segments')
    parser.add_argument('--json_file_path', help='Path to the JSON file', required=True)
    parser.add_argument('--en_file_path', help='Path to the English content file', required=True)
    parser.add_argument('--ch_file_path', help='Path to the Chinese content file', required=True)
    parser.add_argument('--output_dir', help='Path to the output directory', required=True)
    args = parser.parse_args()

    # Call the aligner function
    aligner(args.json_file_path, args.en_file_path, args.ch_file_path, args.output_dir)