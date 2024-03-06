import re
import os
import argparse
import spacy
import subator_constants
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(f"{__name__}.log", mode="w", encoding="utf-8")
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]

def ch_len(str):
    length = 0
    i = 0
    while i < len(str):
        if not str[i].isascii():
            length += 1
            i += 1
        else:
            length += 1
            i += 1
            while i < len(str) and str[i].isascii() and str[i] != ' ':
                i += 1
    return length

def split_sentence_according_to_pattern(sentence, pattern):
    fragments = re.split(pattern, sentence)
    logger.debug(f"            Fragments after splitting by pattern: {fragments}")
    # After splitting by pattern, there must be odd number of fragments
    if len(fragments) % 2 == 0:
        logger.error(f"            Number of fragments after splitting by pattern is even")
        exit(1)
    last_fragment = fragments[-1]
    fragments = [''.join(fragments) for fragments in zip(fragments[0::2], fragments[1::2])]
    fragments.append(last_fragment)
    fragments = [fragment for fragment in fragments if fragment]
    
    logger.debug(f"            Fragments after zipping: {fragments}")
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

def merge_by_num(fragments, num_fragments, len_func):
    logger.debug(f"        Merging fragments by number {num_fragments}: {fragments}")

    if len(fragments) < num_fragments:
        logger.error(f"        Number of fragments is less than {num_fragments}")
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

    logger.debug(f"        Fragments after merging: {fragments}")
    return fragments

# i.e. Iteratively merge the two shortest consecutive fragments if the length of the merged fragment is less than 2/3 of the MAX_FRAGMENT_LENGTH
# If exists a fragment that is shorter than 1/6, merge them with preceding fragment unless the length of the merged fragment is longer than the MAX_FRAGMENT_LENGTH
def merge_by_length(fragments, len_func, language):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH if language == 'ch' else subator_constants.MAX_EN_FRAGMENT_LENGTH
    logger.debug(f"        Merging fragments by length {MAX_FRAGMENT_LENGTH}: {fragments}")
    i = 0

    if max([len_func(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        logger.error(f'        Max fragment length is too long')
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
   
    logger.debug(f"        Fragments after merging: {fragments}")
    return fragments

def get_spans(sentence, nlp, len_func, language):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH if language == 'ch' else subator_constants.MAX_EN_FRAGMENT_LENGTH
    logger.debug('        Using spacy to split the sentence into spans')
    if sentence == '':
        logger.error("        Empty sentence")
        exit(1)
    stop_sets = ['nsubj', 'dobj', 'prep', 'aux:asp', 'case', 'cop',  'advcl', 'punct', 'acomp', 'mark', 'nsubjpass', 'agent', 'dep'] # 
    start_sets = ['cc']
    doc = nlp(sentence)

    for token in doc:
        logger.debug(f'        {token.text} -- {token.dep_}')

    if len(doc) < 2:
        logger.error(f'        Only one token in the sentence')
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
        logger.error(f'        Spacy failed to get the spans')
        exit(1)
    
    # do some merge, because the size of all_possible_fragments is exponential to the number of spans
    # ...
    if len(spans) > 20:
        logger.warning(f'        Too much spans {len(spans)}, merge to 20')
        spans = merge_by_num(spans, 20, len_func)
    
    for i in range(len(spans)):
        if len_func(spans[i]) > MAX_FRAGMENT_LENGTH:
            logger.error(f'        Span {i} is too long: {len_func(spans[i])}')
            exit(1)

    logger.debug(f'        Spans: {spans}')
    
    return spans     

def split_fragment_into_two_fragments(sentence, nlp, len_func, language):
    if sentence == '':
        logger.error("        Empty sentence")
        exit(1)
    logger.debug(f"        Splitting fragment: {sentence}")
    spans = get_spans(sentence, nlp, len_func, language)
    fragments = merge_by_num(spans, 2, len_func)
    return fragments     

def split_sentence_by_length(sentence, nlp, len_func, language):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH if language == 'ch' else subator_constants.MAX_EN_FRAGMENT_LENGTH
    if sentence == '':
        logger.error("        Empty sentence")
        exit(1)
    logger.debug(f"        Sentence: {sentence}")
    logger.debug(f"        Splitting sentence by max length: {MAX_FRAGMENT_LENGTH}")
    
    if language == 'ch':
        punctuation_pattern = r'([。，！？；])'
    elif language == 'en':
        punctuation_pattern = r'([.,!?;]\s)'
    else:
        logger.error(f"Invalid language: {language}")
        exit(1)

    if len_func(sentence) <= MAX_FRAGMENT_LENGTH:
        logger.debug(f"        No need to split")
        logger.debug(f"        Result: {sentence}")
        return [sentence]
    
    # First split the sentence according to punctuation
    fragments = split_sentence_according_to_pattern(sentence, punctuation_pattern)
    logger.debug(f"        Fragments after splitting by punctuation: {fragments}")

    # If still not satisfied the MAX_FRAGMENT_LENGTH condition
    # Iteratively split the longest fragment into fragments that less than MAX_FRAGMENT_LENGTH.
    # If the iteration does not change the number of fragments, just throw an error
    while max([len_func(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        new_fragments = []
        for fragment in fragments:
            if len_func(fragment) > MAX_FRAGMENT_LENGTH:
                new_fragments.extend(split_fragment_into_two_fragments(fragment, nlp, len_func, language))
            else:
                new_fragments.append(fragment)
        fragments = new_fragments
        logger.debug(f"        Fragments after iteration: {fragments}")

    # No fragments longer than MAX_FRAGMENT_LENGTH should exist
    # Try to merge the fragments to satisfy the preferred condition
    # Performing in-sentence merging first can make better fragments
    fragments = merge_by_length(fragments, len_func, language)

    # Done
    logger.debug(f"        Result: {fragments}")
    return fragments

def join_spans(spans):
    result = spans[0]
    for i in range(1, len(spans)):
            result += sep(spans[i-1], spans[i]) + spans[i]
    return result

def get_all_possible_fragments(spans, n):
    if n <= 0 or len(spans) < n:
        return []

    def divide_helper(spans, n):
        if n == 1:
            yield [join_spans(spans)]
            return

        for i in range(1, len(spans)):
            for rest in divide_helper(spans[i:], n - 1):
                yield [join_spans(spans[:i])] + rest

    return list(divide_helper(spans, n))

def cal_loss(fragments, ratio, len_func, language):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH if language == 'ch' else subator_constants.MAX_EN_FRAGMENT_LENGTH
    ratio_sum = sum(ratio)
    len_sentence = sum([len_func(fragment) for fragment in fragments])
    loss = 0
    for i in range(len(fragments)):
        loss += abs(ratio[i]/ratio_sum - len_func(fragments[i])/len_sentence)
        if len_func(fragments[i]) > MAX_FRAGMENT_LENGTH:
            loss += 1
    return loss

def split_sentence_by_ratio(sentence, nlp, ratio, len_func, language):
    logger.debug(f"        Splitting sentence by ratio: {ratio}")
    spans = get_spans(sentence, nlp, len_func, language)
    all_possible_fragments = get_all_possible_fragments(spans, len(ratio))

    min_loss = float('inf')
    best_fragments_index = 0
    for i, fragments in enumerate(all_possible_fragments):
        loss = cal_loss(fragments, ratio, len_func, language)
        if loss < min_loss:
            min_loss = loss
            best_fragments_index = i
    logger.debug(f"        Best fragments: {all_possible_fragments[best_fragments_index]}")
    logger.debug(f"        Loss: {min_loss}")
    return all_possible_fragments[best_fragments_index]

def get_ratio(spans, len_func):
    len_sum = sum([len_func(span) for span in spans])
    return [len_func(span)/len_sum for span in spans]

def split_sentence(ch_sentence, en_sentence, ch_nlp, en_nlp):
    MAX_CH_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH
    MAX_EN_FRAGMENT_LENGTH = subator_constants.MAX_EN_FRAGMENT_LENGTH

    ch_fragments = []
    en_fragments = []

    # If the length of the sentence is bigger than the MAX_FRAGMENT_LENGTH, split the sentence into smaller fragments
    if ch_len(ch_sentence) > MAX_CH_FRAGMENT_LENGTH or len(en_sentence) > MAX_EN_FRAGMENT_LENGTH:
        if ch_len(ch_sentence) > MAX_CH_FRAGMENT_LENGTH:
            logger.info(f"    Chinese sentence length: {ch_len(ch_sentence)}, bigger than {MAX_CH_FRAGMENT_LENGTH}")
        if len(en_sentence) > MAX_EN_FRAGMENT_LENGTH:
            logger.info(f"    English sentence length: {len(en_sentence)}, bigger than {MAX_EN_FRAGMENT_LENGTH}")
        ch_fragments = split_sentence_by_length(ch_sentence, ch_nlp, ch_len, 'ch')
        en_fragments = split_sentence_by_length(en_sentence, en_nlp, len, 'en')
        
        if len(ch_fragments) >= len(en_fragments):
            ratio = get_ratio(ch_fragments, ch_len)
            en_fragments = split_sentence_by_ratio(en_sentence, en_nlp, ratio, len, 'en')
        elif len(en_fragments) > len(ch_fragments):
            ratio = get_ratio(en_fragments, len)
            ch_fragments = split_sentence_by_ratio(ch_sentence, ch_nlp, ratio, ch_len, 'ch')
    # No need to split the sentence
    else:
        logger.info("    No need to split the sentence")
        ch_fragments.append(ch_sentence)
        en_fragments.append(en_sentence)
    return ch_fragments, en_fragments

def spliter(en_path, ch_path, output_dir=False):
    # Read the English and Chinese sentences
    en_sentences = read_file(en_path)
    ch_sentences = read_file(ch_path)
    if len(en_sentences) != len(ch_sentences):
        logger.error(f"Number of English sentences ({len(en_sentences)}) is not equal to the number of Chinese sentences ({len(ch_sentences)})")
        exit(1)
    num_sentences = len(en_sentences)

    # Load the spacy model
    en_nlp = spacy.load(f"{subator_constants.SPACY_EN_MODEL}")
    ch_nlp = spacy.load(f"{subator_constants.SPACY_CH_MODEL}")

    # Split the sentences into fragments using spacy
    en_fragments = []
    ch_fragments = []
    for i in range(num_sentences):
        logger.info(f"Splitting sentence {i+1}/{num_sentences}")
        ch_sentence = ch_sentences[i]
        en_sentence = en_sentences[i]
        logger.info(f"    {en_sentences[i]}")
        logger.info(f"    {ch_sentences[i]}")
        ch_sentence_splited, en_sentence_splited = split_sentence(ch_sentence, en_sentence, ch_nlp, en_nlp)
        ch_sentence_splited = eliminate_punctuation(ch_sentence_splited)
        en_sentence_splited = [fragment.strip() for fragment in en_sentence_splited if fragment.strip()]
        logger.info(f"    Fragments: ")
        logger.info(f"    {ch_sentence_splited}")
        logger.info(f"    {en_sentence_splited}")
        logger.info('')
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
    args = parser.parse_args()
    
    # Call the slicer function
    spliter(args.en_path, args.ch_path, args.output_dir)