import argparse
import os
import subator_constants
import re
import sys
import json
from deepmultilingualpunctuation import PunctuationModel

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(f"{__name__}.log", mode="w", encoding="utf-8")
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

def get_clean_words(text):
    text = text.split()
    text = [re.sub(r"(?<!\d)[.,;:!?](?!\d)", "", word) for word in text]
    return text

def get_clean_word(word):
    word = get_clean_words(word)
    if len(word) > 1:
        logger.error(f"Word {word} has more than one clean word.")
        exit(1)
    elif len(word) == 0:
        logger.error(f"Word {word} has no clean word.")
        exit(1)
    return word[0]

def process_labeled_words(labeled_words):
    sentences = []
    sentence_words = []
    for word, label, _ in labeled_words:
        if label in ['.', '?', ':', '-']:
            sentence_words.append(word)
            sentences.append(' '.join(sentence_words))
            sentence_words = []
        elif label == ',':
            if word[-1] in [',']:
                sentence_words.append(word)
            else:
                sentence_words.append(word+',')
        else:
            assert label == '0'
            sentence_words.append(word)
    if sentence_words:
        sentences.append(' '.join(sentence_words))
    logger.info(f"Segmented sentences: {sentences}")
    return sentences

def segment_line(line, model):
    MAX_LINE_LENGTH = subator_constants.MAX_EN_FRAGMENT_LENGTH*2
    clean_words = get_clean_words(line)
    clean_line = ' '.join(clean_words)
    sentences = []
    if len(clean_line) > MAX_LINE_LENGTH:
        logger.info(f"Line is too long: {len(clean_line)} > {MAX_LINE_LENGTH}")
        logger.info(f'    {clean_line}')
        labeled_words = model.predict(clean_words)
        segmented_line = process_labeled_words(labeled_words)
        logger.info(f'    Segmented line:')
        for sl in segmented_line:
            logger.info(f'    {sl}')
        sentences.extend(segmented_line)
    else:
        sentences.append(clean_line)
    return sentences

def segment_lines(lines):
    if subator_constants.PUNCTUATION_MODEL_PATH == "":
        model = PunctuationModel()
    else:
        model = PunctuationModel(model=subator_constants.PUNCTUATION_MODEL_PATH)
    
    sentences = []
    for line in lines:
        sentences.extend(segment_line(line, model))
    sentences = [sentence.strip() for sentence in sentences]
    sentences = [sentence for sentence in sentences if sentence]
    return sentences

def preprocess_transcription(text):
    text = text.split()
    lines = []
    line = ''
    for word in text:
        if word[-1] in ['.', '!', '?', ':']:
            line += word
            lines.append(line)
            line = ''
        else:
            line += word + ' '
    if line:
        lines.append(line)
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    return lines
    
def merge_short_lines(sentences):
    # Merge short lines from end to start
    sentences.reverse()
    i = 0
    while i+1 < len(sentences):
        if len(sentences[i+1].split()) < 5:
            if sentences[i+1][-1] in [',', '.', '!', '?', ':']:
                sentences[i] = sentences[i+1] + ' ' + sentences[i]
            else:
                sentences[i] = sentences[i+1] + ', ' + sentences[i]
            del sentences[i+1]
        else:
            i += 1
    sentences.reverse()

    # i = 0
    # while i+1 < len(sentences):
    #     if sentences[i][-1].isdigit() and sentences[i+1][0].isdigit():
    #         sentences[i] = sentences[i] + ', ' + sentences[i+1]
    #         del sentences[i+1]
    #     else:
    #         i += 1


    MAX_LINE_LENGTH = subator_constants.MAX_EN_FRAGMENT_LENGTH
    i = 0
    while i+1 < len(sentences):
        if len(sentences[i]) + len(sentences[i+1]) < int(MAX_LINE_LENGTH):
            logger.info(f"Merge sentence {sentences[i]} with {sentences[i+1]}")
            # clean_word can't distinguish between decimal points and periods after numbers. If the last word of a sentence is a number, it will follow a period. No need to add a period.
            if sentences[i][-1] in [',', '.', '!', '?', ':']:
                sentences[i] = sentences[i] + ' ' + sentences[i+1]
            else:
                sentences[i] = sentences[i] + '. '+ sentences[i+1]
            del sentences[i+1]
        else:
            i += 1
    logger.info('')
    return sentences

def process_transcription(text):
    lines = preprocess_transcription(text)
    sentences = segment_lines(lines)
    sentences = merge_short_lines(sentences)
    return sentences

def process_timestamps(word_segments):
    timestamps = []
    for segment in word_segments:
        # Handle the bug of WhisperX
        word = segment['word']
        if word == 'JR.:':
            word = 'JR.'
        word = get_clean_word(word)

        start_time = segment['start'] if 'start' in segment else None
        end_time = segment['end'] if 'end' in segment else None
        timestamps.append({'word': word, 'start': start_time, 'end': end_time})
    
    i = 0
    while i < len(timestamps):
        if timestamps[i]['start'] is None:
            j = i-1
            while j >= 0 and timestamps[j]['end'] is None:
                j -= 1
            k = i+1
            while k < len(timestamps) and timestamps[k]['start'] is None:
                k += 1
            
            start_time_of_words = timestamps[j]['end'] if j >= 0 else 0
            end_time_of_words = timestamps[k]['start'] if k < len(timestamps) else timestamps[j]['end']
            duration = end_time_of_words - start_time_of_words
            word_count = k - j - 1
            word_duration = duration / word_count
            for l in range(j+1, k):
                timestamps[l]['start'] = timestamps[l-1]['end']
                timestamps[l]['end'] = timestamps[l]['start'] + word_duration
            i = k
        else:
            i += 1
    check_timestamps(word_segments, timestamps)

    # whisperx may have a bug that ',' is a word. Remove it.
    timestamps = [timestamp for timestamp in timestamps if timestamp['word']]
    return timestamps

def eliminate_end_puncuation(text):
    if len(text) > 0 and text[-1] in ',.':
        return text[:-1]
    return text

def check_clean_words(words1, words2):
    logger.info('Checking clean words...')
    if len(words1) != len(words2):
        logger.error(f'Cheking clean words failed: Lengths are not equal: {len(words1)} != {len(words2)}')
        exit(1)
    for i in range(len(words1)):
        logger.debug(f'Checking {words1[i]} == {words2[i]}')
        if eliminate_end_puncuation(words1[i]) != eliminate_end_puncuation(words2[i]):
            logger.error(f'Cheking clean words failed: Words are not equal: {words1[i]} != {words2[i]}')
            exit(1)
    logger.info('Cheking clean words passed: All words are equal')

def check_timestamps(word_segments, time_stamps):
    logger.info('Checking timestamps...')
    if len(word_segments) != len(time_stamps):
        logger.error(f'Cheking timestamps failed: Lengths are not equal: {len(word_segments)} != {len(time_stamps)}')
        exit(1)
    for i in range(len(word_segments)):
        # logger.info(f'{word_segments[i]["word"]} {word_segments[i]["start"] if "start" in word_segments[i] else ""} {word_segments[i]["end"] if "end" in word_segments[i] else ""}')
        # logger.info(f'{time_stamps[i]["word"]} {time_stamps[i]["start"]} {time_stamps[i]["end"]}')
        if 'start' in word_segments[i] and word_segments[i]['start'] != time_stamps[i]['start']:
            logger.error(f'Cheking timestamps failed: Start times are not equal: {word_segments[i]["start"]} != {time_stamps[i]["start"]}')
            exit(1)
        if 'end' in word_segments[i] and word_segments[i]['end'] != time_stamps[i]['end']:
            logger.error(f'Cheking timestamps failed: End times are not equal: {word_segments[i]["end"]} != {time_stamps[i]["end"]}')
            exit(1)
    logger.info('Cheking timestamps passed: All times are equal')

def transcriber(autdio_path, output_dir):
    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    model = subator_constants.TRANSCRIBE_MODEL
    model_path = subator_constants.TRANSCRIBE_MODEL_PATH
    print_progress = True
    language = subator_constants.TRANSCRIBE_LANGUAGE
    align_model = subator_constants.TRANSCRIBE_ALIGN_MODEL
    # Execute this command line to transcribe the audio file
    command = ''
    if model_path == '':
        command = f"whisperx {autdio_path} --model {model} --print_progress {print_progress} --language {language} --align_model {align_model} --output_dir {output_dir}"
    else:
        command = f"whisperx {autdio_path} --model {model} --print_progress {print_progress} --language {language} --align_model {align_model} --output_dir {output_dir} --model_dir {model_path}"
    logger.info(command)
    os.system(command)

    if not os.path.exists(os.path.join(output_dir, "audio.txt")) and not os.path.exists(os.path.join(output_dir, "audio.json")):
        logger.error("Transcription failed.")
        exit(1)
    
    text_path = os.path.join(output_dir, "audio.txt")
    with open(text_path, 'r') as f:
        text = f.read()
    sentences = process_transcription(text)
    

    json_path = os.path.join(output_dir, "audio.json")
    with open(json_path, 'r') as f:
        audio_data = json.load(f)
    
    timestamps = process_timestamps(audio_data['word_segments'])

    words1 = []
    for sentence in sentences:
        words1.extend(sentence.split())
    words2 = []
    for timestamp in timestamps:
        words2.append(timestamp['word'])
    check_clean_words(words1, words2)
    
    sencences_path = os.path.join(output_dir, "sentences.txt")
    with open(sencences_path, 'w') as f:
        for sentence in sentences:
            f.write(sentence + '\n')
    logger.info(f"Sentences are saved to {sencences_path}")

    timestamps_path = os.path.join(output_dir, "timestamps.json")
    with open(timestamps_path, 'w') as f:
        json.dump(timestamps, f, ensure_ascii=False, indent=4)
    logger.info(f"Timestamps are saved to {timestamps_path}")

    logger.info("Transcription completed.")

if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Transcribe the audio")
    parser.add_argument("--audio_path", help="Path to the audio file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    args = parser.parse_args()
    
    # Call the transcriber function
    transcriber(args.audio_path, args.output_dir)