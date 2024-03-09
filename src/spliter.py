import re
import os
import argparse
import spacy
import subator_constants
import logging
import sys
import json

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
        sentences = f.readlines()
    sentences = [sentence.strip() for sentence in sentences]
    return sentences

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
    if not (span1[-1].isascii() and span2[0].isascii()):
        return ''
    return ' '

def eliminate_punctuation(fragment):
    punctuation_pattern = r'([。，！？；：“”《》、（）])'
    fragment = re.sub(punctuation_pattern, ' ', fragment)
    fragment = fragment.strip()
    return fragment

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
def merge_ch_fragments_by_length(fragments):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH
    logger.debug(f"        Merging fragments by length {MAX_FRAGMENT_LENGTH}: {fragments}")
    
    i = 0
    if max([ch_len(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        logger.error(f'        Max fragment length is too long')
        exit(1)

    i = 0
    while i+1 < len(fragments):
        if (ch_len(fragments[i]) < int(MAX_FRAGMENT_LENGTH * 0.3)) and ch_len(fragments[i] + fragments[i+1]) <= MAX_FRAGMENT_LENGTH:
            fragments[i] = fragments[i] + fragments[i+1]
            del fragments[i+1]
        else:
            i += 1

    i = 0
    while i+1 < len(fragments):
        if ch_len(fragments[i]) + ch_len(fragments[i+1]) <= int(MAX_FRAGMENT_LENGTH * 0.8):
            fragments[i] = fragments[i] + fragments[i+1]
            del fragments[i+1]
        else:
            i += 1
    
    logger.debug(f"        Fragments after merging: {fragments}")
    return fragments

def get_all_possible_fragments(spans, n):
    if n <= 0 or len(spans) < n:
        return []

    def divide_helper(spans, n):
        if n == 1:
            yield [' '.join(spans)]
            return

        for i in range(1, len(spans)):
            for rest in divide_helper(spans[i:], n - 1):
                yield [' '.join(spans[:i])] + rest

    return list(divide_helper(spans, n))

def cal_loss(spans, ratio):
    ratio_sum = sum(ratio)
    len_fragment = sum([len(span) for span in spans])
    loss = 0
    for i in range(len(spans)):
        loss += abs(ratio[i]/ratio_sum - len(spans[i])/len_fragment)
    return loss

def get_ratio(spans, len_func):
    len_sum = sum([len_func(span) for span in spans])
    return [len_func(span)/len_sum for span in spans]

def get_ch_spans(fragment, nlp):
    logger.debug('        Using spacy to split the fragment into spans')
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH
    if fragment == '':
        logger.error("        Empty fragment")
        exit(1)

    stop_sets = ['nsubj', 'dobj', 'prep', 'aux:asp', 'case', 'cop',  'advcl', 'punct', 'acomp', 'mark', 'nsubjpass', 'agent', 'dep'] # 
    start_sets = ['cc']

    doc = nlp(fragment)

    for token in doc:
        logger.debug(f'        {token.text} -- {token.dep_}')

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
    
    assert span_start == len(doc)

    if len(spans) == 1:
        logger.error(f'        Spacy failed to get the spans')
        exit(1)
    
    # do some merge, because the size of all_possible_fragments is exponential to the number of spans
    # ...
    if len(spans) > 15:
        logger.warning(f'        Too much spans {len(spans)}, merge to 15')
        spans = merge_by_num(spans, 15, ch_len)
    
    for i in range(len(spans)):
        if ch_len(spans[i]) > MAX_FRAGMENT_LENGTH:
            logger.error(f'        Span {i} is too long: {ch_len(spans[i])}')
            exit(1)

    logger.debug(f'        Spans: {spans}')
    
    return spans     

def split_ch_fragment_into_two_fragments(fragment, nlp):
    if fragment == '':
        logger.error("        Empty fragment")
        exit(1)
    logger.debug(f"        Splitting fragment: {fragment}")
    spans = get_ch_spans(fragment, nlp)
    fragments = merge_by_num(spans, 2, ch_len)
    return fragments  
   
def split_ch_sentence_by_length(sentence, nlp):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH
    if sentence == '':
        logger.error("        Empty sentence")
        exit(1)
    logger.debug(f"        Sentence: {sentence}")
    logger.debug(f"        Splitting sentence by max length: {MAX_FRAGMENT_LENGTH}")
    
    punctuation_pattern = r'([。，！？；])'

    if ch_len(sentence) <= MAX_FRAGMENT_LENGTH:
        logger.debug(f"        No need to split")
        logger.debug(f"        Result: {sentence}")
        return [sentence]
    
    # First split the sentence according to punctuation
    fragments = split_sentence_according_to_pattern(sentence, punctuation_pattern)
    logger.debug(f"        Fragments after splitting by punctuation: {fragments}")

    # If still not satisfied the MAX_FRAGMENT_LENGTH condition
    # Iteratively split the longest fragment into fragments that less than MAX_FRAGMENT_LENGTH.
    # If the iteration does not change the number of fragments, just throw an error
    while max([ch_len(fragment) for fragment in fragments]) > MAX_FRAGMENT_LENGTH:
        new_fragments = []
        for fragment in fragments:
            if ch_len(fragment) > MAX_FRAGMENT_LENGTH:
                new_fragments.extend(split_ch_fragment_into_two_fragments(fragment, nlp))
            else:
                new_fragments.append(fragment)
        fragments = new_fragments
        logger.debug(f"        Fragments after iteration: {fragments}")

    # No fragments longer than MAX_FRAGMENT_LENGTH should exist
    # Try to merge the fragments to satisfy the preferred condition
    # Performing in-sentence merging first can make better fragments
    fragments = merge_ch_fragments_by_length(fragments)

    # Done
    logger.debug(f"        Result: {fragments}")
    return fragments

def split_en_fragment_by_ratio(en_fragment, ratio):
    logger.debug(f"        Splitting sentence by ratio: {ratio}")
    spans = en_fragment.split()
    if len(spans) > 15:
        logger.warning(f'        Too much spans {len(spans)}, merge to 15')
        spans = merge_by_num(spans, 15, len)
    all_possible_fragments = get_all_possible_fragments(spans, len(ratio))

    min_loss = float('inf')
    best_fragments_index = 0
    for i, fragments in enumerate(all_possible_fragments):
        loss = cal_loss(fragments, ratio)
        if loss < min_loss:
            min_loss = loss
            best_fragments_index = i
    logger.debug(f"        Best fragments: {all_possible_fragments[best_fragments_index]}")
    logger.debug(f"        Loss: {min_loss}")
    return all_possible_fragments[best_fragments_index]

def split_en_fragment_by_length(en_fragment):
    MAX_FRAGMENT_LENGTH = subator_constants.MAX_EN_FRAGMENT_LENGTH
    if len(en_fragment) > MAX_FRAGMENT_LENGTH:
        logger.info(f"    English fragment length: {len(en_fragment)}, bigger than {MAX_FRAGMENT_LENGTH}")
        logger.info(f"    {en_fragment}")
        num_fragments = len(en_fragment)//MAX_FRAGMENT_LENGTH + 1
        ratio = [1/num_fragments for _ in range(num_fragments)]
        fragments = split_en_fragment_by_ratio(en_fragment, ratio)
    else:
        fragments = [en_fragment]
    return fragments
    
def split_sentence(ch_sentence, en_sentence, ch_nlp):
    MAX_CH_FRAGMENT_LENGTH = subator_constants.MAX_CH_FRAGMENT_LENGTH

    splited_sentence = []

    # If the length of the chinese sentence is bigger than the MAX_FRAGMENT_LENGTH, split the sentence into smaller fragments
    if ch_len(ch_sentence) > MAX_CH_FRAGMENT_LENGTH:
        logger.info(f"    Chinese sentence length: {ch_len(ch_sentence)}, bigger than {MAX_CH_FRAGMENT_LENGTH}")
        ch_fragments = split_ch_sentence_by_length(ch_sentence, ch_nlp)
        assert max([ch_len(fragment) for fragment in ch_fragments]) <= MAX_CH_FRAGMENT_LENGTH
        
        ratio = get_ratio(ch_fragments, ch_len)
        en_fragments = split_en_fragment_by_ratio(en_sentence,ratio)

        assert len(ch_fragments) == len(en_fragments)

        for i in range(len(ch_fragments)):
            ch_fragment = ch_fragments[i]
            en_fragment = en_fragments[i]
            fragment = {'ch': ch_fragment, 'en': split_en_fragment_by_length(en_fragment)}
            splited_sentence.append(fragment)
    # If the length of the chinese sentence is smaller than the MAX_FRAGMENT_LENGTH, no need to split the sentence
    else:
        logger.info("    No need to split the sentence")
        ch_fragment = ch_sentence
        en_fragment = en_sentence
        fragment = {'ch': ch_fragment, 'en': split_en_fragment_by_length(en_fragment)}
        splited_sentence.append(fragment)
    
    for fragment in splited_sentence:
        fragment['ch'] = eliminate_punctuation(fragment['ch'])
        fragment['en'] = [fragment.strip() for fragment in fragment['en']]
    return splited_sentence

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
        if eliminate_end_puncuation(words1[i]) != eliminate_end_puncuation(words2[i]):
            logger.error(f'Cheking clean words failed: Words are not equal: {words1[i]} != {words2[i]}')
            exit(1)
    logger.info('Cheking clean words passed: All words are equal')

def spliter(en_path, ch_path, output_dir):
    # Read the English and Chinese sentences
    en_sentences = read_file(en_path)
    ch_sentences = read_file(ch_path)
    if len(en_sentences) != len(ch_sentences):
        logger.error(f"Number of English sentences ({len(en_sentences)}) is not equal to the number of Chinese sentences ({len(ch_sentences)})")
        exit(1)
    num_sentences = len(en_sentences)

    # Load the spacy model
    # en_nlp = spacy.load(f"{subator_constants.SPACY_EN_MODEL}")
    ch_nlp = spacy.load(f"{subator_constants.SPACY_CH_MODEL}")

    # Split the sentences into fragments using spacy, one chinese fragment may correspond to multiple english fragments
    fragments = []
    for i in range(num_sentences):
        logger.info(f"Splitting sentence {i+1}/{num_sentences}")
        ch_sentence = ch_sentences[i]
        en_sentence = en_sentences[i]
        logger.info(f"    {en_sentence}")
        logger.info(f"    {ch_sentence}")
        splited_sentence = split_sentence(ch_sentence, en_sentence, ch_nlp)
        logger.info(f"    Fragments: ")
        for fragment in splited_sentence:
            logger.info(f"    {fragment['ch']}")
            logger.info(f"    {fragment['en']}")
            logger.info('')
        fragments.extend(splited_sentence)

    words1 = []
    words2 = []
    for sentence in en_sentences:
        words1.extend(sentence.split())
    for fragment in fragments:
        for sentence in fragment['en']:
            words2.extend(sentence.split())
    check_clean_words(words1, words2)

    # Write the splited sentences to the output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(output_dir, "fragments.json"), 'w', encoding='utf-8') as f:
        json.dump(fragments, f, ensure_ascii=False, indent=4)

    logger.info(f"Fragments written to {output_dir}/fragments.json")
    logger.info("")

if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Slice the English and Chinese sentences into smaller fragments")
    parser.add_argument("--en_path", help="Path to the English sentences file", required=True)
    parser.add_argument("--ch_path", help="Path to the Chinese sentences file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    args = parser.parse_args()
    
    # Call the slicer function
    spliter(args.en_path, args.ch_path, args.output_dir)