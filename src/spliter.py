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

def split_sentence_according_to_pattern(sentence, pattern, verbose):
    fragments = re.split(pattern, sentence)
    if verbose:
        print(f"            Fragments after splitting by pattern: {fragments}")
    # After splitting by pattern, there must be odd number of fragments
    if len(fragments) % 2 == 0:
        print(f"            Number of fragments after splitting by pattern is even")
        exit(1)
    last_fragment = fragments[-1]
    fragments = [''.join(fragments) for fragments in zip(fragments[0::2], fragments[1::2])]
    fragments.append(last_fragment)
    fragments = [fragment for fragment in fragments if fragment]
    if verbose:
        print(f"            Fragments after zipping: {fragments}")
    return fragments

def sep(span1, span2):

    no_sep_follow = [',', '.', '!', '?', ';', ':', "'", '"', "n't", "'s", '-', '%', ' ']
    no_sep_current = ['$', '-', ' ']

    if span1 == '' or span2 == '':
        return ''
    
    if span1.endswith('gon') and span2.startswith('na'):
        return ''
    if not (span1[-1].isascii() and span2[0].isascii()):
        return ''
    
    if span2.startswith(tuple(no_sep_follow)):
        return ''
    if span1.endswith(tuple(no_sep_current)):
        return ''
    
    if span2[0].isdigit() and span1[-1] == '.':
        return ''
    return ' '

def eliminate_punctuation(fragments):
    punctuation_pattern = r'([。，！？；：“”《》、（）])'
    fragments = [re.sub(punctuation_pattern, ' ', fragment) for fragment in fragments]
    fragments = [fragment for fragment in fragments if fragment]
    fragments = [fragment.strip() for fragment in fragments]
    return fragments

def merge_by_num(fragments, num_fragments, len_func, verbose):
    if verbose:
        print(f"        Merging fragments by number {num_fragments}: {fragments}")

    if len(fragments) < num_fragments:
        print(f"        Number of fragments is less than {num_fragments}")
        exit(1)

    while len(fragments) > num_fragments:
        min_length = float('inf')
        min_index = -1
        for i in range(len(fragments)-1):
            if len_func(fragments[i]) + len_func(fragments[i+1]) < min_length:
                min_length = len_func(fragments[i]) + len_func(fragments[i+1])
                min_index = i
        fragments[min_index] = fragments[min_index] + sep(fragments[min_index], fragments[min_index+1]) + fragments[min_index+1]
        del fragments[min_index+1]

    if verbose:
        print(f"        Fragments after merging: {fragments}")
    return fragments

# i.e. Iteratively merge the two shortest consecutive fragments if the length of the merged fragment is less than 2/3 of the MAX_FRAGMENT_LENGTH
# If exists a fragment that is shorter than 1/6, merge them with preceding fragment unless the length of the merged fragment is longer than the MAX_FRAGMENT_LENGTH
def merge_by_length(fragments, MAX_FRAGMENT_LENGTH, len_func, verbose):
    if verbose:
        print(f"        Merging fragments by length {MAX_FRAGMENT_LENGTH}: {fragments}")
    i = 0

    if max([len_func(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        print(f'        Max fragment length is too long')
        exit(1)

    i = 0
    while i+1 < len(fragments):
        if len_func(fragments[i]) + len_func(fragments[i+1]) <= int(MAX_FRAGMENT_LENGTH * 0.8):
            fragments[i] = fragments[i] + sep(fragments[i], fragments[i+1]) + fragments[i+1]
            del fragments[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(fragments):
        if (len_func(fragments[i]) < int(MAX_FRAGMENT_LENGTH * 0.3) or len_func(fragments[i+1]) < int(MAX_FRAGMENT_LENGTH * 0.3)) and len_func(fragments[i] + fragments[i+1]) <= MAX_FRAGMENT_LENGTH:
            fragments[i] = fragments[i] + sep(fragments[i], fragments[i+1]) + fragments[i+1]
            del fragments[i+1]
        else:
            i += 1
   
    if verbose:
        print(f"        Fragments after merging: {fragments}")
    return fragments

def get_spans(sentence, nlp, len_func, MAX_FRAGMENT_LENGTH, verbose):
    print('        using spacy to split the sentence into spans')
    if sentence == '':
        print("        Empty sentence")
        exit(1)
    stop_sets = ['nsubj', 'dobj', 'prep', 'aux:asp', 'case', 'cop',  'advcl', 'punct', 'acomp', 'mark', 'nsubjpass', 'agent', 'dep'] # 
    start_sets = ['cc']
    doc = nlp(sentence)

    for token in doc:
        if verbose:
            print(f'        {token.text} -- {token.dep_}')

    if len(doc) < 2:
        print(f'        Only one token in the sentence')
        exit(1)

    spans = []
    span_start = 0
    for token in doc:
        if token.is_sent_end:
            span = doc[span_start:token.i+1]
            spans.append(span.text)
            span_start = token.i+1
        elif token.dep_ in stop_sets:
            if token.text == '-' or (token.i+1 < len(doc) and doc[token.i+1].text == '-'):
                continue
            span = doc[span_start:token.i+1]
            spans.append(span.text)
            span_start = token.i+1
        elif token.dep_ in start_sets or token.is_sent_start:
            if span_start != token.i:
                span = doc[span_start:token.i]
                spans.append(span.text)
            span_start = token.i

    i = 0
    while i+1 < len(spans):
        if spans[i+1] in [',', '.', '!', '?', ';', ':', "'", '"', '-', '%']:
            spans[i] = spans[i] + spans[i+1]
            del spans[i+1]
        else:
            i += 1

    if len(spans) == 1:
        print(f'        Spacy failed to get the spans')
        exit(1)
    
    # do some merge, because the size of all_possible_fragments is exponential to the number of spans
    # ...
    if len(spans) > 20:
        print(f'        Too much spans {len(spans)}, merge to 20')
        spans = merge_by_num(spans, 20, len_func, verbose)
    
    for i in range(len(spans)):
        if len_func(spans[i]) > MAX_FRAGMENT_LENGTH:
            print(f'        Span {i} is too long: {len_func(spans[i])}')
            exit(1)

    if verbose:
        print(f'        Spans: {spans}')
    
    return spans     

def split_fragment_into_two_fragments(sentence, nlp, len_func, MAX_FRAGMENT_LENGTH, verbose):
    if sentence == '':
        print("        Empty sentence")
        exit(1)
    if verbose:
        print(f"        Splitting fragment: {sentence}")
    spans = get_spans(sentence, nlp, len_func, MAX_FRAGMENT_LENGTH, verbose)
    fragments = merge_by_num(spans, 2, len_func, verbose)
    return fragments     

def split_sentence_by_length(sentence, nlp, MAX_FRAGMENT_LENGTH, lang, verbose):
    if sentence == '':
        print("        Empty sentence")
        exit(1)
    if verbose:
        print(f"        Sentence: {sentence}")
        print(f"        Splitting sentence by max length: {MAX_FRAGMENT_LENGTH}")
    
    if lang == 'ch':
        len_func = ch_len
        punctuation_pattern = r'([。，！？；])'
    elif lang == 'en':
        len_func = len
        punctuation_pattern = r'([.,!?;]\s)'
    else:
        print(f"Invalid language: {lang}")
        exit(1)

    if len_func(sentence) <= MAX_FRAGMENT_LENGTH:
        if verbose:
            print(f"        No need to split")
            print(f"        Result: {sentence}")
        return [sentence]
    # First split the sentence according to punctuation
    fragments = split_sentence_according_to_pattern(sentence, punctuation_pattern, verbose)
    if verbose:
        print(f"        Fragments after splitting by punctuation: {fragments}")

    # If still not satisfied the MAX_FRAGMENT_LENGTH condition
    # Iteratively split the longest fragment into fragments that less than MAX_FRAGMENT_LENGTH.
    # If the iteration does not change the number of fragments, just throw an error
    while max([len_func(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        new_fragments = []
        for fragment in fragments:
            if len_func(fragment) > MAX_FRAGMENT_LENGTH:
                new_fragments.extend(split_fragment_into_two_fragments(fragment, nlp, len_func, MAX_FRAGMENT_LENGTH, verbose))
            else:
                new_fragments.append(fragment)
        fragments = new_fragments
        if verbose:
            print(f"        Fragments after iteration: {fragments}")

    # No fragments longer than MAX_FRAGMENT_LENGTH should exist
    # Try to merge the fragments to satisfy the preferred condition
    # Performing in-sentence merging first can make better fragments
    fragments = merge_by_length(fragments, MAX_FRAGMENT_LENGTH, len_func, verbose)

    # Done
    if verbose:
        print(f"        Result: {fragments}")
    return fragments

def join_spans(spans, language):
    result = spans[0]
    for i in range(1, len(spans)):
        if language == 'ch':
            result += spans[i]
        elif language == 'en':
            result += sep(spans[i-1], spans[i]) + spans[i]
        else:
            print(f"Invalid language: {language}")
            exit(1)
    return result

def divide_spans_into_fragments(spans, n, language):
    if n <= 0 or len(spans) < n:
        return []

    def divide_helper(spans, n):
        if n == 1:
            yield [join_spans(spans, language)]
            return

        for i in range(1, len(spans)):
            for rest in divide_helper(spans[i:], n - 1):
                yield [join_spans(spans[:i], language)] + rest

    return list(divide_helper(spans, n))

def cal_loss(fragments, ratio, len_func, MAX_FRAGMENT_LENGTH):
    ratio_sum = sum(ratio)
    len_sentence = sum([len_func(fragment) for fragment in fragments])
    loss = 0
    for i in range(len(fragments)):
        loss += abs(ratio[i]/ratio_sum - len_func(fragments[i])/len_sentence)
        if len_func(fragments[i]) > MAX_FRAGMENT_LENGTH:
            loss += 1
    return loss

def split_sentence_by_ratio(sentence, nlp, ratio, len_func, MAX_FRAGMENT_LENGTH, verbose):
    language = 'ch' if len_func == ch_len else 'en'
    
    if verbose:
        print(f"        Splitting sentence by ratio: {ratio}")
    spans = get_spans(sentence, nlp, len_func, MAX_FRAGMENT_LENGTH, verbose)
    all_possible_fragments = divide_spans_into_fragments(spans, len(ratio), language)

    min_loss = float('inf')
    best_fragments_index = 0
    for i, fragments in enumerate(all_possible_fragments):
        loss = cal_loss(fragments, ratio, len_func, MAX_FRAGMENT_LENGTH)
        if loss < min_loss:
            min_loss = loss
            best_fragments_index = i
    if verbose:
        print(f"        Best fragments: {all_possible_fragments[best_fragments_index]}")
        print(f"        Loss: {min_loss}")
    return all_possible_fragments[best_fragments_index]

def get_ratio(spans, len_func):
    len_sum = sum([len_func(span) for span in spans])
    return [len_func(span)/len_sum for span in spans]

def split_sentence(ch_sentence, en_sentence, ch_nlp, en_nlp, MAX_CH_FRAGMENT_LENGTH, MAX_EN_FRAGMENT_LENGTH, verbose):
    ch_fragments = []
    en_fragments = []

    # If the length of the sentence is bigger than the MAX_FRAGMENT_LENGTH, split the sentence into smaller fragments
    if ch_len(ch_sentence) > MAX_CH_FRAGMENT_LENGTH or len(en_sentence) > MAX_EN_FRAGMENT_LENGTH:
        if verbose:
            if ch_len(ch_sentence) > MAX_CH_FRAGMENT_LENGTH:
                print(f"    Chinese sentence length: {ch_len(ch_sentence)}, bigger than {MAX_CH_FRAGMENT_LENGTH}")
            if len(en_sentence) > MAX_EN_FRAGMENT_LENGTH:
                print(f"    English sentence length: {len(en_sentence)}, bigger than {MAX_EN_FRAGMENT_LENGTH}")
        ch_fragments = split_sentence_by_length(ch_sentence, ch_nlp, MAX_CH_FRAGMENT_LENGTH, 'ch', verbose)
        en_fragments = split_sentence_by_length(en_sentence, en_nlp, MAX_EN_FRAGMENT_LENGTH, 'en', verbose)
        
        if len(ch_fragments) >= len(en_fragments):
            ratio = get_ratio(ch_fragments, ch_len)
            en_fragments = split_sentence_by_ratio(en_sentence, en_nlp, ratio, len, MAX_EN_FRAGMENT_LENGTH, verbose)
        elif len(en_fragments) > len(ch_fragments):
            ratio = get_ratio(en_fragments, len)
            ch_fragments = split_sentence_by_ratio(ch_sentence, ch_nlp, ratio, ch_len, MAX_CH_FRAGMENT_LENGTH, verbose)
    # No need to split the sentence
    else:
        print("No need to split the sentence")
        ch_fragments.append(ch_sentence)
        en_fragments.append(en_sentence)
    return ch_fragments, en_fragments

def spliter(en_path, ch_path, output_dir, verbose=False):
    MAX_CH_FRAGMENT_LENGTH = 33
    MAX_EN_FRAGMENT_LENGTH = 80
    # Read the English and Chinese sentences
    en_sentences = read_file(en_path)
    ch_sentences = read_file(ch_path)
    if len(en_sentences) != len(ch_sentences):
        print(f"Number of English sentences ({len(en_sentences)}) is not equal to the number of Chinese sentences ({len(ch_sentences)})")
        exit(1)
    num_sentences = len(en_sentences)

    # Load the spacy model
    en_nlp = spacy.load("en_core_web_trf")
    ch_nlp = spacy.load("zh_core_web_trf")

    # Split the sentences into fragments using spacy
    en_fragments = []
    ch_fragments = []
    for i in range(num_sentences):
        print(f"Splitting sentence {i+1}/{num_sentences}")
        ch_sentence = ch_sentences[i]
        en_sentence = en_sentences[i]
        print(f"    {en_sentences[i]}")
        print(f"    {ch_sentences[i]}")
        ch_sentence_splited, en_sentence_splited = split_sentence(ch_sentence, en_sentence, ch_nlp, en_nlp, MAX_CH_FRAGMENT_LENGTH, MAX_EN_FRAGMENT_LENGTH, verbose)
        ch_sentence_splited = eliminate_punctuation(ch_sentence_splited)
        en_sentence_splited = [fragment.strip() for fragment in en_sentence_splited if fragment.strip()]
        print(f"    Fragments: ")
        print(f"    {ch_sentence_splited}")
        print(f"    {en_sentence_splited}")
        ch_fragments.extend(ch_sentence_splited)
        en_fragments.extend(en_sentence_splited)

    # Write the splited sentences to the output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, "en_splited.txt"), "w", encoding="utf-8") as f:
        for fragment in en_fragments:
            f.write(fragment + "\n")
    with open(os.path.join(output_dir, "ch_splited.txt"), "w", encoding="utf-8") as f:
        for fragment in ch_fragments:
            f.write(fragment + "\n")


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Slice the English and Chinese sentences into smaller fragments")
    parser.add_argument("--en_path", help="Path to the English sentences file", required=True)
    parser.add_argument("--ch_path", help="Path to the Chinese sentences file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--verbose", help="Print the debug information", action="store_true")
    args = parser.parse_args()
    
    # Call the slicer function
    spliter(args.en_path, args.ch_path, args.output_dir, args.verbose)