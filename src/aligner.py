import json
import os
import argparse
import srt
import re
from datetime import timedelta

def load_json(file_path):
    # Load the JSON file
    with open(file_path, "r", encoding="utf-8") as file:
        audio_data = json.load(file)

    word_dict = audio_data["word_segments"]

    all_words = []
    all_start_times = []
    all_end_times = []
    for i, word in enumerate(word_dict):
        all_words.append(word["word"])
        if 'start' in word:
            all_start_times.append(word["start"])
        else:
            print(f"Start time not found for word {i+1}: {word}")
            if i == 0:
                all_start_times.append(0)
            else:
                all_start_times.append(None)
        if 'end' in word:
            all_end_times.append(word["end"])
        else:
            print(f"End time not found for word {i+1}: {word}")
            all_end_times.append(None)
    
    if len(all_words) != len(all_start_times) or len(all_words) != len(all_end_times):
        print(f"Length of words ({len(all_words)}), start times ({len(all_start_times)}), and end times ({len(all_end_times)}) do not match.")
        exit(1)
    
    # for i in range(len(all_words)):
    #     if all_start_times[i] is None:
    #         if i == 0:
    #             all_start_times[i] = 0
    #         else:
    #             all_start_times[i] = all_end_times[i-1]
    #         # print(f"Setting start time for word {all_words[i]} to {all_start_times[i]}")
    #     if all_end_times[i] is None:
    #         if i == len(all_words) - 1:
    #             all_end_times[i] = all_start_times[i] + 1
    #         else:
    #             for j in range(i+1, len(all_words)):
    #                 if all_start_times[j] is not None:
    #                     all_end_times[i] = all_start_times[j]
    #                     break
    #         # print(f"Setting end time for word {all_words[i]} to {all_end_times[i]}")

    # if len(all_words) != len(all_start_times) or len(all_words) != len(all_end_times):
    #     print(f"Length of words ({len(all_words)}), start times ({len(all_start_times)}), and end times ({len(all_end_times)}) do not match.")
    #     exit(1)

    return all_words, all_start_times, all_end_times


def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]
    
   
def aligner(json_file_path, en_file_path, ch_file_path, output_dir):
    # Load the JSON file
    all_words, words_start_times, words_end_times = load_json(json_file_path)
    
    # Read the English and Chinese content
    en_contents = read_file(en_file_path)
    ch_contents = read_file(ch_file_path)
    
    if len(en_contents) != len(ch_contents):
        print(f"Length of English contents ({len(en_contents)}) and Chinese contents ({len(ch_contents)}) do not match.")
        exit(1)
    

    # Check if contents are matched with the words
    i = 0
    for content in en_contents:
        content_words = content.split(' ')
        for content_word in content_words:
            # print(f'Checking the word: {content_word} with the word: {all_words[i]}')
            if content_word != all_words[i]:
                print(f'In the content: {content}, the word: {content_word} does not match with the word: {all_words[i]}')
                print(f'content_word: {content_word}, all_words[i]: {all_words[i]}, all_words[i+1]: {all_words[i+1]}')
                # spacy will tokenize content. Words like aa-aa may be multiple tokens. Here is a bypass way
                if all_words[i].startswith(content_word):
                    print(f"Word '{all_words[i]}' starts with the content word '{content_word}'")
                    all_words.insert(i+1, all_words[i][len(content_word):])
                    all_words[i] = content_word
                    words_start_times.insert(i+1, words_start_times[i])
                    words_end_times.insert(i+1, words_end_times[i])
                # spacy will tokenize content. So, we can't distinguish between digit. digit with digit.digit, here is a bypass way
                elif content_word.startswith(all_words[i]):
                    content = content.replace(content_word, content_word[:len(all_words[i])] + ' ' + content_word[len(all_words[i]):], 1)
                    print(f"content: {content}")
                    i += 1
                else:
                    print(f"Can't find the word '{content_word}' in the word list")
                    exit(1)
            i += 1
    
    print("All words are matched with the contents")
    
    # Get the start and end times of the contents
    contents_start_times = []
    contents_end_times = []
    i = 0
    for content in en_contents:
        content_words = content.split(' ')
        if words_start_times[i]:
            contents_start_times.append(words_start_times[i])
        else:
            print(f"In the content: {content}")
            print(f"Start time not found for word {i+1}: {all_words[i]}")
            # Find the nearest start time
            j = i
            while j > 0 and not words_start_times[j]:
                j -= 1
            if j == 0:
                contents_start_times.append(0)
            else:
                contents_start_times.append(words_end_times[j])
            print(f"Nearest start time: word_end_times[{j}], word: {all_words[j]}")
        i += len(content_words)
        if words_end_times[i-1]:
            contents_end_times.append(words_end_times[i-1])
        else:
            print(f"In the content: {content}")
            print(f"End time not found for word {i}: {all_words[i-1]}")
            # Find the nearest end time
            j = i
            while j < len(all_words) and not words_end_times[j]:
                j += 1
            if j == len(all_words):
                print(f"Searching hit the end of the word list, please check the last word")
                contents_end_times.append(contents_start_times[-1])
            else:
                contents_end_times.append(words_start_times[j])
            print(f"Nearest end time: word_start_times[{j}], word: {all_words[j]}")
    
    i = 0
    for i in range(len(en_contents)-1):
        if contents_start_times[i+1] < contents_end_times[i]:
            print(f"Content {i+1} starts before content {i} ends")
            print(f"Content {i}: {en_contents[i]}")
            print(f"Content {i} ends at {contents_end_times[i]}")
            print(f"Content {i+1}: {en_contents[i+1]}")
            print(f"Content {i+1} starts at {contents_start_times[i+1]}")
            # exit(1)
            contents_start_times[i+1] = contents_end_times[i]
    # Create en subtitles
    en_subtitles = []
    for i, content in enumerate(en_contents):
        en_subtitles.append(srt.Subtitle(index=i+1, content=content, start=timedelta(seconds=contents_start_times[i]), end=timedelta(seconds=contents_end_times[i])))

    # Create ch subtitles
    ch_subtitles = []
    for i, content in enumerate(ch_contents):
        ch_subtitles.append(srt.Subtitle(index=i+1, content=content, start=timedelta(seconds=contents_start_times[i]), end=timedelta(seconds=contents_end_times[i])))

    # Create ch_en subtitles
    ch_en_subtitles = []
    for i, content in enumerate(en_contents):
        ch_en_subtitles.append(srt.Subtitle(index=i+1, content=ch_contents[i] + '\n' + content, start=timedelta(seconds=contents_start_times[i]), end=timedelta(seconds=contents_end_times[i])))

    print("Subtitles are created")

    # Write the subtitles to the output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(os.path.join(output_dir, "en.srt"), 'w', encoding='utf-8') as f:
        f.write(srt.compose(en_subtitles))

    with open(os.path.join(output_dir, "ch.srt"), 'w', encoding='utf-8') as f:
        f.write(srt.compose(ch_subtitles))

    with open(os.path.join(output_dir, "ch_en.srt"), 'w', encoding='utf-8') as f:
        f.write(srt.compose(ch_en_subtitles))

    print("Subtitles are written to the output directory")


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