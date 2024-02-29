import re
import os
import argparse
import spacy

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]

def ch_len(str):
    # Count the length of the string, but treat two consecutive english characters as one character
    length = 0
    i = 0
    while i < len(str):
        if str[i].isascii():
            length += 1
            if i+1 < len(str) and str[i+1].isascii():
                i += 1
        else:
            length += 1
        i += 1
    return length

def split_content_according_to_pattern(content, pattern, verbose):
    chunks = re.split(pattern, content)
    if verbose:
        print(f"            Chunks after splitting by pattern: {chunks}")
    # After splitting by pattern, there must be odd number of chunks
    if len(chunks) % 2 == 0:
        print(f"            Number of chunks after splitting by pattern is even")
        exit(1)
    last_chunk = chunks[-1]
    chunks = [''.join(chunks) for chunks in zip(chunks[0::2], chunks[1::2])]
    chunks.append(last_chunk)
    chunks = [chunk for chunk in chunks if chunk]
    if verbose:
        print(f"            Chunks after zipping: {chunks}")
    return chunks

def sep(chunk1, chunk2):

    no_sep_follow = [',', '.', '!', '?', ';', ':', "'", '"', "n't", "'s", '-', '%', ' ']
    no_sep_current = ['$', '-', ' ']

    if chunk1 == '' or chunk2 == '':
        return ''
    
    if chunk1.endswith('gon') and chunk2.startswith('na'):
        return ''
    if not (chunk1[-1].isascii() and chunk2[0].isascii()):
        return ''
    
    if chunk2.startswith(tuple(no_sep_follow)):
        return ''
    if chunk1.endswith(tuple(no_sep_current)):
        return ''
    
    if chunk2[0].isdigit() and chunk1[-1] == '.':
        return ''
    return ' '


def eliminate_punctuation(chunks):
    punctuation_pattern = r'([。，！？；：“”《》、])'
    chunks = [re.sub(punctuation_pattern, ' ', chunk) for chunk in chunks]
    chunks = [chunk for chunk in chunks if chunk]
    chunks = [chunk.strip() for chunk in chunks]
    chunks = [chunk for chunk in chunks if chunk]
    return chunks

def merge_by_num(chunks, num_chunks, len_func, verbose):
    if verbose:
        print(f"        Merging chunks by number: {chunks}")

    i = 0
    while i+1 < len(chunks):
        if chunks[i+1] in [',', '.', '!', '?', ';', ':', "'", '"', '-', '%']:
            chunks[i] = chunks[i] + chunks[i+1]
            del chunks[i+1]
        else:
            i += 1

    if len(chunks) < num_chunks:
        print(f"        Number of chunks is less than {num_chunks}")
        exit(1)

    while len(chunks) > num_chunks:
        min_length = float('inf')
        min_index = -1
        for i in range(len(chunks)-1):
            if len_func(chunks[i]) + len_func(chunks[i+1]) < min_length:
                min_length = len_func(chunks[i]) + len_func(chunks[i+1])
                min_index = i
        chunks[min_index] = chunks[min_index] + sep(chunks[min_index], chunks[min_index+1]) + chunks[min_index+1]
        del chunks[min_index+1]

    if verbose:
        print(f"        Chunks after merging: {chunks}")
    return chunks

# i.e. Iteratively merge the two shortest consecutive chunks if the length of the merged chunk is less than 2/3 of the max length
# If exists a chunks that is shorter than 1/6, merge them with preceding chunk unless the length of the merged chunk is longer than the max length
def merge_by_length(chunks, MAX_CHUNK_LENGTH, len_func, verbose):
    if verbose:
        print(f"        Merging chunks by length: {chunks}")
    i = 0
    while i+1 < len(chunks):
        if chunks[i+1] in [',', '.', '!', '?', ';', ':', "'", '"', '-', '%']:
            chunks[i] = chunks[i] + chunks[i+1]
            del chunks[i+1]
        else:
            i += 1

    if max([len_func(chunk) for chunk in chunks]) > MAX_CHUNK_LENGTH:
        print(f'        Max chunk length is too long after merge punctuation')
        exit(1)

    i = 0
    while i+1 < len(chunks):
        if len_func(chunks[i]) + len_func(chunks[i+1]) <= int(MAX_CHUNK_LENGTH * 0.8):
            chunks[i] = chunks[i] + sep(chunks[i], chunks[i+1]) + chunks[i+1]
            del chunks[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(chunks):
        if (len_func(chunks[i]) < int(MAX_CHUNK_LENGTH * 0.3) or len_func(chunks[i+1]) < int(MAX_CHUNK_LENGTH * 0.3)) and len_func(chunks[i] + chunks[i+1]) <= MAX_CHUNK_LENGTH:
            chunks[i] = chunks[i] + sep(chunks[i], chunks[i+1]) + chunks[i+1]
            del chunks[i+1]
        else:
            i += 1
    # i = 0
    # while i+1 < len(chunks):
    #     if (len_func(chunks[i]) < int(MAX_CHUNK_LENGTH * 0.1) or len_func(chunks[i+1]) < int(MAX_CHUNK_LENGTH * 0.1)):
    #         chunks[i] = chunks[i] + sep(chunks[i], chunks[i+1]) + chunks[i+1]
    #         del chunks[i+1]
    #     else:
    #         i += 1

    if verbose:
        print(f"        Chunks after merging: {chunks}")
    return chunks


def split_chunk(content, nlp, len_func, verbose):
    print('using spacy')
    if content == '':
        print("        Empty content")
        exit(1)

    if verbose:
        print(f'        Split: {content}')
    stop_sets = ['dobj', 'pobj', 'advcl', 'aux:asp', 'case', 'conj', 'mark', 'punct', 'acomp', 'ccomp'] # 
    start_sets = ['cc', 'prep']
    doc = nlp(content)
    
    for token in doc:
        if verbose:
            print(f'        {token.text} -- {token.dep_}')

    chunks = []
    chunk = ''
    for token in doc:
        if token.dep_ in stop_sets or token.is_sent_end:
            chunk = chunk + sep(chunk, token.text) + token.text
            chunks.append(chunk)
            chunk = ''
        elif token.dep_ in start_sets or token.is_sent_start:
            if chunk != '':
                chunks.append(chunk)
            chunk = token.text
        else:
            chunk = chunk + sep(chunk, token.text) + token.text
    
    if len(doc) < 2:
        print(f'        Failed to split')
        exit(1)
    
    i = 0
    while i+1 < len(chunks):
        if chunks[i+1] in [',', '.', '!', '?', ';', ':', "'", '"', '-', '%']:
            chunks[i] = chunks[i] + chunks[i+1]
            del chunks[i+1]
        else:
            i += 1

    if len(chunks) == 1:
        print(f'        Spacy failed to split, force split into two chunks')
        chunks = []
        chunk = ''
        for i in range(len(doc)//2):
            chunk = chunk + sep(chunk, doc[i].text) + doc[i].text
        chunks.append(chunk)
        chunk = ''
        for i in range(len(doc)//2, len(doc)):
            chunk = chunk + sep(chunk, doc[i].text) + doc[i].text
        chunks.append(chunk)
    
    if verbose:
        print(f'        Split: {chunks}')
    chunks = merge_by_num(chunks, 2, len_func, verbose)
    return chunks     

def split_sentence_by_length(content, nlp, MAX_CHUNK_LENGTH, lang, verbose):
    if content == '':
        print("        Empty content")
        exit(1)
    if verbose:
        print(f"        Sentence: {content}")
        print(f"        Splitting sentence by max length: {MAX_CHUNK_LENGTH}")
    
    if lang == 'ch':
        len_func = ch_len
        punctuation_pattern = r'([。，！？；])'
    elif lang == 'en':
        len_func = len
        punctuation_pattern = r'([.,!?;]\s)'
    else:
        print(f"Invalid language: {lang}")
        exit(1)

    if len_func(content) <= MAX_CHUNK_LENGTH:
        if verbose:
            print(f"        No need to split")
            print(f"        Result: {content}")
        return [content]
    # First split the content according to punctuation
    chunks = split_content_according_to_pattern(content, punctuation_pattern, verbose)
    if verbose:
        print(f"        Chunks after splitting by punctuation: {chunks}")

    # If still not satisfied the MAX_CHUNK_LENGTH condition
    # Iteratively split the longest chunk into chunks that less than 2/3 of the max length using hanlp.
    # If the iteration does not change the number of chunks, just throw an error
    while max([len_func(chunk) for chunk in chunks]) > MAX_CHUNK_LENGTH:
        new_chunks = []
        for chunk in chunks:
            if len_func(chunk) > MAX_CHUNK_LENGTH:
                new_chunks.extend(split_chunk(chunk, nlp, len_func, verbose))
            else:
                new_chunks.append(chunk)
        chunks = new_chunks
        if verbose:
            print(f"        Chunks after iteration: {chunks}")

    # No chunks longer than MAX_CHUNK_LENGTH should exist
    # Try to merge the chunks to satisfy the preferred condition
    # Performing in-sentence merging first can make better chunking
    chunks = merge_by_length(chunks, MAX_CHUNK_LENGTH, len_func, verbose)

    # Done
    if verbose:
        print(f"        Result: {chunks}")
    return chunks

def split_chunks_by_num(chunks, nlp, num_chunks, len_func, verbose):
    if verbose:
        print(f"        Splitting chunks by number {num_chunks}: ")
        print(f"        {chunks}")
    while len(chunks) < num_chunks + 1:
        # Find the longest chunk
        max_length = 0
        max_index = -1
        for i in range(len(chunks)):
            if len_func(chunks[i]) > max_length:
                max_length = len_func(chunks[i])
                max_index = i
        if verbose:
            print(f"        Longest chunk: {chunks[max_index]}")
        chunks = chunks[:max_index] + split_chunk(chunks[max_index], nlp, len_func, verbose) + chunks[max_index+1:]
        if verbose:
            print(f"        Chunks after iteration: {chunks}")
    chunks = merge_by_num(chunks, num_chunks, len_func, verbose)
    return chunks


def split_content(ch_content, en_content, ch_nlp, en_nlp, MAX_CH_CHUNK_LENGTH, MAX_EN_CHUNK_LENGTH, verbose):
    ch_chunks = []
    en_chunks = []

    # If the length of the content is bigger than the MAX_CHUNK_LENGTH, split the content into smaller chunks
    if ch_len(ch_content) > MAX_CH_CHUNK_LENGTH or len(en_content) > MAX_EN_CHUNK_LENGTH:
        if verbose:
            if ch_len(ch_content) > MAX_CH_CHUNK_LENGTH:
                print(f"    Chinese content length: {ch_len(ch_content)}, bigger than {MAX_CH_CHUNK_LENGTH}")
            if len(en_content) > MAX_EN_CHUNK_LENGTH:
                print(f"    English content length: {len(en_content)}, bigger than {MAX_EN_CHUNK_LENGTH}")
        ch_chunks = split_sentence_by_length(ch_content, ch_nlp, MAX_CH_CHUNK_LENGTH, 'ch', verbose)
        en_chunks = split_sentence_by_length(en_content, en_nlp, MAX_EN_CHUNK_LENGTH, 'en', verbose)
        
        while len(ch_chunks) > len(en_chunks):
            en_chunks = split_chunks_by_num(en_chunks, en_nlp, len(ch_chunks), len, verbose)
        while len(en_chunks) > len(ch_chunks):
            ch_chunks = split_chunks_by_num(ch_chunks, ch_nlp, len(en_chunks), ch_len, verbose)
    # No need to split the content
    else:
        print("No need to split the content")
        ch_chunks.append(ch_content)
        en_chunks.append(en_content)
    return ch_chunks, en_chunks

def spliter(en_path, ch_path, output_dir, verbose=False):
    MAX_CH_CHUNK_LENGTH = 33
    MAX_EN_CHUNK_LENGTH = 80
    # Read the English and Chinese sentences
    en_contents = read_file(en_path)
    ch_contents = read_file(ch_path)
    if len(en_contents) != len(ch_contents):
        print(f"Number of English contents ({len(en_contents)}) is not equal to the number of Chinese contents ({len(ch_contents)})")
        exit(1)
    num_contents = len(en_contents)

    # Load the spacy model
    en_nlp = spacy.load("en_core_web_trf")
    ch_nlp = spacy.load("zh_core_web_trf")

    # Split the contents into chunks using spacy
    en_contents_splited = []
    ch_contents_splited = []
    for i in range(num_contents):
        print(f"Splitting content {i+1}/{num_contents}")
        print(f"    {en_contents[i]}")
        print(f"    {ch_contents[i]}")
        ch_chunks, en_chunks = split_content(ch_contents[i], en_contents[i], ch_nlp, en_nlp, MAX_CH_CHUNK_LENGTH, MAX_EN_CHUNK_LENGTH, verbose)
        ch_chunks = eliminate_punctuation(ch_chunks)
        en_chunks = [chunk.strip() for chunk in en_chunks if chunk.strip()]
        print(f"    Chunks: ")
        print(f"    {ch_chunks}")
        print(f"    {en_chunks}")
        ch_contents_splited.extend(ch_chunks)
        en_contents_splited.extend(en_chunks)

    # Write the splited contents to the output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, "en_splited.txt"), "w", encoding="utf-8") as f:
        for chunk in en_contents_splited:
            f.write(chunk + "\n")
    with open(os.path.join(output_dir, "ch_splited.txt"), "w", encoding="utf-8") as f:
        for chunk in ch_contents_splited:
            f.write(chunk + "\n")


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Slice the English and Chinese content")
    parser.add_argument("--en_path", help="Path to the English content file", required=True)
    parser.add_argument("--ch_path", help="Path to the Chinese content file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--verbose", help="Print the debug information", action="store_true")
    args = parser.parse_args()
    
    # Call the slicer function
    spliter(args.en_path, args.ch_path, args.output_dir, args.verbose)