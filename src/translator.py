import os
import argparse
import sys
import spacy
from zhipuai import ZhipuAI
import random
from http import HTTPStatus
import dashscope
import subator_constants
import logging
import time
import re
from openai import OpenAI
from deepmultilingualpunctuation import PunctuationModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(f"{__name__}.log", mode="w", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

gpt_client = None

def is_sentence_start(sent):
    start_set = ['so', 'and', 'but', 'or', 'if', 'when', 'because', 'then', 'i']
    if len(sent) > 8 and sent[0].text.lower() in start_set:
        for token in sent[:8]:
            if token.dep_ == "nsubj":
                return True
    return False

def is_sentence_end(sent):
    end_set = ['.', '!', '?', ':', ';', ',']
    if len(sent) > 8 and sent[0].text.lower() in end_set:
        for token in sent[:8]:
            if token.dep_ == "nsubj":
                return True
    return False
    
def get_sentences(sentences_file_path):
    # Read the file
    if not os.path.exists(sentences_file_path):
        logger.error(f"File '{sentences_file_path}' not found.")
        exit(1)
    with open(sentences_file_path, 'r', encoding='utf-8') as f:
        sentences = f.readlines()
    return sentences

def call_gpt_api(messages, api_key):
    logger.debug("        Calling GPT API")
    content_translated = ''
    token_used = 0
    response_valid = True
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        content_translated = response.choices[0].message.content
        token_used = response.usage.total_tokens
    except Exception as e:
        logger.error(f'        Error calling GPT API: {e}')
        content_translated = '调用GPT API出错。'
        response_valid = False

    logger.debug(f"        Response: {content_translated}")
    return content_translated, token_used, response_valid

def call_qwen_api(messages, api_key):
    logger.debug("        Calling Qwen API")
    content_translated = ''
    token_used = 0
    response_valid = True
    try:
        dashscope.api_key = api_key
        response = dashscope.Generation.call(
            model='qwen-plus',
            messages=messages,
            # set the random seed, optional, default to 1234 if not set
            seed=random.randint(1, 10000),
            result_format='message',  # set the result to be "message" format.
        )
        if response.status_code == HTTPStatus.OK:
            content_translated = response.output.choices[0].message.content
            token_used = response.usage.total_tokens
        else:
            logger.error('        Error calling Qwen API: Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
            ))
            content_translated = '调用Qwen API出错。'
            response_valid = False
            if response.status_code == 429:
                # wait for 5 seconds and retry
                time.sleep(5)
    except Exception as e:
        logger.error(f'        Error calling Qwen API: {e}')
        content_translated = '调用Qwen API出错。'
        response_valid = False
    
    logger.debug(f"        Response: {content_translated}")
    return content_translated, token_used, response_valid

def call_glm_api(messages, api_key):
    logger.debug("        Calling GLM API")
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
        logger.error(f'        Error calling GLM API: {e}')
        content_translated = '调用GLM API出错。'
        response_valid = False

    logger.debug(f"        Response: {content_translated}")
    return content_translated, token_used, response_valid

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

def is_good_response(sentence_translated, sentence):
    ratio = ch_len(sentence_translated)/len(sentence.split())
    logger.debug(f"    Ratio: {ratio}")
    RATIO_LIMIT = subator_constants.CH_EN_RATIO_LIMIT
    if len(sentence.split()) <= 10:
        RATIO_LIMIT += 0.5
    if '\n' in sentence_translated:
        logger.debug(f"    Response contains multiple lines.")
        return False
    if 'API出错' in sentence_translated or (('翻译' in sentence_translated or '意思是' in sentence_translated or '意译' in sentence_translated or '含义' in sentence_translated) and '：' in sentence_translated):
        logger.debug(f"    Response contains unexpected content.")
        return False
    if ratio > RATIO_LIMIT:
        logger.debug(f"    Response is longer than expected.")
        return False
    return True

def call_llm_api(llm, messages, api_key):
    logger.debug(f"    Calling {llm} API with messages: {messages}")
    if llm == "gpt":
        return call_gpt_api(messages, api_key)
    elif llm == "qwen":
        return call_qwen_api(messages, api_key)
    elif llm == "glm":
        return call_glm_api(messages, api_key)
    else:
        logger.error(f"Invalid llm: {llm}")
        exit(1)
  
def translate_sentence(sentence, llm, api_key, user_prompt, window_before_str, window_after_str):
    RETRY_LIMIT = subator_constants.TRANSLATE_RETRY_LIMIT
    token_used = 0

    system_content = f"你是一名翻译专家，双语字幕制作专家，{user_prompt}。请使用地道流畅简洁的语言表达，尽量使用简单句。"
    user_content = f"这是上文：{window_before_str}。这是下文：{window_after_str}。请将下面这个英文句子片段翻译为中文：{sentence}。除了该片段的翻译结果不要输出任何语句。"
    message = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]
    logger.info(f"Sentence: {sentence}")
    sentence_translated = '句子未翻译。'

    sentence_translated, token_usage, response_valid = call_llm_api(llm, message, api_key)
    token_used += token_usage
    num_retries = 0

    user_content = f"请将下面这个英文句子片段翻译为中文：{sentence}。除了该片段的翻译结果不要输出任何语句，包括但不限于(翻译结果为：，翻译为中文为：，意思是：)。"
    message = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]
    while not response_valid or not is_good_response(sentence_translated, sentence):
        if num_retries >= RETRY_LIMIT:
            logger.warning(f"    Retry limit reached.")
            break
        logger.debug(f"    Retrying...")
        sentence_translated, token_usage, response_valid = call_llm_api(llm, message, api_key)
        token_used += token_usage
        num_retries += 1

    sentence_translated = sentence_translated.replace("您", "你")
    return sentence_translated, token_used

def translate_all(sentences, llm, api_key, user_prompt):
    WINDOW_SIZE = subator_constants.TRANSLATE_WINDOW_SIZE
    tot_tokens = 0
    window_before = []
    window_before_str = ''
    window_after = []
    window_after_str = ''
    # Call the API to translate the sentences
    sentences_translated = []
    for i, sentence in enumerate(sentences):
        logger.info(f"Translating sentence {i+1}/{len(sentences)}")
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
            logger.info(f"    Bad response, Please check the response. Then modify potentially erroneous lines in ch.txt.")
        logger.info(f"    Original: {sentence}")
        logger.info(f"    Translated: {sentence_translated}")
        logger.info('')
        tot_tokens += token_used
        sentences_translated.append(sentence_translated)

    sentences_translated = [i.strip() for i in sentences_translated]
    
    return sentences_translated, tot_tokens
        
def translator(sentences_file_path, output_dir, api_key, user_prompt, llm):
    sentences = get_sentences(sentences_file_path)

    # if llm == 'gpt':
    #     global gpt_client
    #     gpt_client = OpenAI(base_url="https://api.chatgptid.net/v1", api_key=api_key)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    sentences_translated, tot_tokens = translate_all(sentences, llm, api_key, user_prompt)

    # Write the translated sentences to a file
    output_file = os.path.join(output_dir, "sentences_translated.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences_translated:
            f.write(sentence + '\n')
    logger.info(f"Translated sentences written to {output_file}")
    logger.info(f"Total tokens used: {tot_tokens}")
    logger.info('')

if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Translate the sentences")
    parser.add_argument("--sentences_file_path", help="Path to the sentences file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--user_prompt", help="User prompt", required=False, default='')
    parser.add_argument("--api_key", help="API key", required=True)
    parser.add_argument("--llm", help="Language model", required=False, default="qwen")
    args = parser.parse_args()

    sentences_file_path = args.sentences_file_path
    output_dir = args.output_dir
    user_prompt = args.user_prompt
    api_key = args.api_key
    llm = args.llm

    # Translate the sentences
    translator(sentences_file_path, output_dir, api_key, user_prompt, llm)