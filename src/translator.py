import os
import argparse
import sys
import spacy
from zhipuai import ZhipuAI
import random
from http import HTTPStatus
import dashscope

def merge_short_lines(sentences, MAX_LINE_LENGTH):
    i = 0
    while i+1 < len(sentences):
        if len(sentences[i]) + len(sentences[i+1]) < int(MAX_LINE_LENGTH*0.8):
            print(f"Merge sentence {sentences[i]} with {sentences[i+1]}")
            sentences[i] = sentences[i] + ' '+ sentences[i+1]
            del sentences[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(sentences):
        if (len(sentences[i]) < int(MAX_LINE_LENGTH*0.25) or len(sentences[i+1]) < int(MAX_LINE_LENGTH*0.25)) and len(sentences[i]) + len(sentences[i+1]) < MAX_LINE_LENGTH:
            print(f"Merge sentence {sentences[i]} with {sentences[i+1]}")
            sentences[i] = sentences[i] + ' '+ sentences[i+1]
            del sentences[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(sentences):
        if (len(sentences[i]) < int(MAX_LINE_LENGTH*0.1) or len(sentences[i+1]) < int(MAX_LINE_LENGTH*0.1)):
            print(f"Merge sentence {sentences[i]} with {sentences[i+1]}")
            sentences[i] = sentences[i] + ' '+ sentences[i+1]
            del sentences[i+1]
        else:
            i += 1

    return sentences

def get_sentences(sentences_file_path, MAX_LINE_LENGTH):
    # Read the file
    if not os.path.exists(sentences_file_path):
        print(f"File '{sentences_file_path}' not found.")
        exit(1)
    with open(sentences_file_path, 'r', encoding='utf-8') as f:
        sentences = f.read()
    
    sentences = ' '.join(sentences.split())

    # Load the spacy model
    en_nlp = spacy.load("en_core_web_trf")
    doc = en_nlp(sentences)
    sentences_fragmented = []
    for i, sent in enumerate(doc.sents):
        if len(sent.text) > MAX_LINE_LENGTH*2:
            print(f"Line {i+1} is too long: {len(sent.text)}")
            print(f"    {sent.text}")
            frag_start = 0
            frags = []
            for i, token in enumerate(sent):
                if i < len(sent)-1 and token.dep_ == "punct" and (sent[i+1].dep_ == "cc" or sent[i+1].dep_ == "nsubj"):
                    if token.text in [',', '.', '!', '?', ':', ';']:
                        span = sent[frag_start:i+1]
                        frags.append(span.text)
                        frag_start = i+1
            span = sent[frag_start:]
            frags.append(span.text)
            for frag in frags:
                print(f"    Split sentence: {frag}")
            print(f"    Longest fragment: {max([len(i) for i in frags])}")
            sentences_fragmented.extend(frags)
        else:
            sentences_fragmented.append(sent.text)

    # strip the sentences
    sentences_fragmented = [i.strip() for i in sentences_fragmented]
    # Merge short lines
    return merge_short_lines(sentences_fragmented, MAX_LINE_LENGTH)

def call_qwen_api(messages, api_key):
    print("        Calling Qwen API")
    content_translated = ''
    token_used = 0
    response_valid = True
    try:
        dashscope.api_key = api_key
        response = dashscope.Generation.call(
            model='qwen-max',
            messages=messages,
            # set the random seed, optional, default to 1234 if not set
            seed=random.randint(1, 10000),
            result_format='message',  # set the result to be "message" format.
        )
        if response.status_code == HTTPStatus.OK:
            content_translated = response.output.choices[0].message.content
            token_used = response.usage.total_tokens
        else:
            print('        Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            content_translated = '调用Qwen API出错。'
            token_used = response.usage.total_tokens
            response_valid = False
    except Exception as e:
        print(f'        Error calling Qwen API: {e}')
        content_translated = '调用Qwen API出错。'
        response_valid = False
    
    print(f"        Response: {content_translated}")
    return content_translated, token_used, response_valid

def call_glm_api(messages, api_key):
    print("        Calling GLM API")
    content_translated = ''
    token_used = 0
    response_valid = True
    try:
        client = ZhipuAI(api_key=api_key) # replace with your own API key
        response = client.chat.completions.create(
            model="glm-4",  # model name
            messages=messages,  # messages
        )
        content_translated = response.choices[0].message.content
        token_used = response.usage.total_tokens
    except Exception as e:
        print(f'        Error calling GLM API: {e}')
        content_translated = '调用GLM API出错。'
        response_valid = False

    print(f"        Response: {content_translated}")
    return content_translated, token_used, response_valid

def ch_len(str):
    # Count the length of the string, but treat two consecutive english characters as one character
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

def is_good_response(sentence_translated, sentence):
    ratio = ch_len(sentence_translated)/len(sentence.split())
    print(f"    Ratio: {ratio}")
    RATIO_LIMIT = 2.8
    if len(sentence.split()) <= 10:
        RATIO_LIMIT = 3
    if '\n' in sentence_translated:
        print(f"    Response contains multiple lines.")
        return False
    if 'API出错' in sentence_translated or '翻译结果' in sentence_translated:
        print(f"    Response contains unexpected content.")
        return False
    if ratio > RATIO_LIMIT:
        print(f"    Response is longer than expected.")
        return False
    # print(f"    Response is good.")
    return True

def translate_sentence(sentence, llm, api_key, user_prompt, window_before_str, window_after_str):
    RETRY_LIMIT = 5
    token_used = 0

    system_content = f"你是一名翻译专家。请使用地道流畅简洁的语言表达，尽量使用简单句，可以意译，避免生硬翻译。人名和地名等专有名词不要翻译。{user_prompt}。"
    user_content = f"这是上文：{window_before_str}。这是下文：{window_after_str}。请将下面这个英文句子片段翻译为中文{sentence}。除了该片段的翻译结果不要输出任何语句。"
    message = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]
    print(f"    Calling API with content: {system_content} {user_content}")
    print(f"    Sentence: {sentence}")
    sentence_translated = '句子未翻译。'
    if llm == "qwen":
        sentence_translated, token_usage, response_valid = call_qwen_api(message, api_key)
        token_used += token_usage
        num_retries = 0

        user_content = f"请将下面这个英文句子片段翻译为中文{sentence}。除了该片段的翻译结果不要输出任何语句，包括但不限于(翻译结果为：，翻译为中文为：)。"
        message = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]
        while not response_valid or not is_good_response(sentence_translated, sentence):
            if num_retries >= RETRY_LIMIT:
                print(f"    Retry limit reached.")
                break
            print(f"    Retrying...")
            sentence_translated, token_usage, response_valid = call_qwen_api(message, api_key)
            token_used += token_usage
            num_retries += 1

    elif llm == "glm":
        sentence_translated, token_used, response_valid = call_glm_api(message, api_key)
        token_used += token_usage
        num_retries = 0

        user_content = f"请将下面这个英文句子片段翻译为中文{sentence}。除了该片段的翻译结果不要输出任何语句，包括但不限于(翻译结果为：，翻译为中文为：)。"
        message = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]
        while not response_valid or not is_good_response(sentence_translated, sentence):
            if num_retries >= RETRY_LIMIT:
                print(f"    Retry limit reached.")
                break
            print(f"    Retrying...")
            sentence_translated, token_usage, response_valid = call_glm_api(message, api_key)
            token_used += token_usage
            num_retries += 1
    else:
        print(f"    Invalid llm: {llm}")
        exit(1)

    sentence_translated = sentence_translated.replace("您", "你")
    return sentence_translated, token_used

def translate_all(sentences, llm, api_key, user_prompt, WINDOW_SIZE=1):
    tot_tokens = 0
    window_before = []
    window_before_str = ''
    window_after = []
    window_after_str = ''
    # Call the API to translate the sentences
    sentences_translated = []
    for i, sentence in enumerate(sentences):
        print(f"Translating sentence {i+1}/{len(sentences)}")
        if i >= WINDOW_SIZE and i < len(sentences)-WINDOW_SIZE:
            window_before = sentences[i-WINDOW_SIZE:i]
            window_before_str = ' '.join(window_before)
            window_after = sentences[i+1:i+1+WINDOW_SIZE]
            window_after_str = ' '.join(window_after)
        else:
            window_before = []
            window_before_str = ''
            window_after = []
            window_after_str = ''
        
        sentence_translated, token_used = translate_sentence(sentence, llm, api_key, user_prompt, window_before_str, window_after_str)
        if not is_good_response(sentence_translated, sentence):
            print(f"    Bad response, Please check the response. Then modify potentially erroneous lines in ch.txt.")
        print(f"    Original: {sentence}")
        print(f"    Translated: {sentence_translated}")
        tot_tokens += token_used
        sentences_translated.append(sentence_translated)

    sentences_translated = [i.strip() for i in sentences_translated]
    
    return sentences_translated, tot_tokens
        


def translator(sentences_file_path, output_dir, api_key, user_prompt, llm):
    WINDOW_SIZE = 1
    MAX_LINE_LENGTH = 80
    
    sentences = get_sentences(sentences_file_path, MAX_LINE_LENGTH)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Write the sentence to a file
    output_file = os.path.join(output_dir, "en.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences:
            f.write(sentence + '\n')

    sentences_translated, tot_tokens = translate_all(sentences, llm, api_key,user_prompt, WINDOW_SIZE)

    # Write the translated sentences to a file
    output_file = os.path.join(output_dir, "ch.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences_translated:
            f.write(sentence + '\n')
    print(f"Translated sentences written to {output_file}")
    print(f"Total tokens used: {tot_tokens}")


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Translate the sentences")
    parser.add_argument("--sentences_file_path", help="Path to the sentences file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--user_prompt", help="User prompt")
    parser.add_argument("--api_key", help="API key", required=True)
    args = parser.parse_args()

    sentences_file_path = args.sentences_file_path
    output_dir = args.output_dir
    user_prompt = args.user_prompt
    api_key = args.api_key

    if user_prompt is None:
        user_prompt = ''

    # Translate the sentences
    translator(sentences_file_path, output_dir, api_key, user_prompt)