import os
import argparse
import sys
import spacy
from zhipuai import ZhipuAI

def merge_short_lines(contents, MAX_LINE_LENGTH):
    i = 0
    while i+1 < len(contents):
        if len(contents[i]) + len(contents[i+1]) < int(MAX_LINE_LENGTH*0.8):
            print(f"Merge sentence {contents[i]} with {contents[i+1]}")
            contents[i] = contents[i] + ' '+ contents[i+1]
            del contents[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(contents):
        if (len(contents[i]) < int(MAX_LINE_LENGTH*0.25) or len(contents[i+1]) < int(MAX_LINE_LENGTH*0.25)) and len(contents[i]) + len(contents[i+1]) < MAX_LINE_LENGTH:
            print(f"Merge sentence {contents[i]} with {contents[i+1]}")
            contents[i] = contents[i] + ' '+ contents[i+1]
            del contents[i+1]
        else:
            i += 1
    
    i = 0
    while i+1 < len(contents):
        if (len(contents[i]) < int(MAX_LINE_LENGTH*0.1) or len(contents[i+1]) < int(MAX_LINE_LENGTH*0.1)):
            print(f"Merge sentence {contents[i]} with {contents[i+1]}")
            contents[i] = contents[i] + ' '+ contents[i+1]
            del contents[i+1]
        else:
            i += 1

    return contents

def get_content(content_path, MAX_LINE_LENGTH):
    # Read the file
    if not os.path.exists(content_path):
        print(f"File '{content_path}' not found.")
        exit(1)
    with open(content_path, 'r', encoding='utf-8') as f:
        all_contents = f.read()
    
    all_contents = ' '.join(all_contents.split())

    # Load the spacy model
    en_nlp = spacy.load("en_core_web_trf")
    doc = en_nlp(all_contents)
    sentences = []
    for i, sent in enumerate(doc.sents):
        if len(sent.text) > MAX_LINE_LENGTH*2:
            print(f"Line {i+1} is too long: {len(sent.text)}")
            print(f"    {sent.text}")
            chunk_start = 0
            chunks = []
            for i, token in enumerate(sent):
                if i < len(sent)-1 and token.dep_ == "punct" and (sent[i+1].dep_ == "cc" or sent[i+1].dep_ == "nsubj"):
                    span = sent[chunk_start:i+1]
                    chunks.append(span.text)
                    chunk_start = i+1
            span = sent[chunk_start:]
            chunks.append(span.text)
            for chunk in chunks:
                print(f"    Split sentence: {chunk}")
            sentences.extend(chunks)
        else:
            sentences.append(sent.text)

    # strip the contents
    sentences = [i.strip() for i in sentences]
    # Merge short lines
    return merge_short_lines(sentences, MAX_LINE_LENGTH)

def translate_all(contents, client, user_prompt, WINDOW_SIZE=2):
    num_tokens = 0
    window_contents = []
    window_contents_str = ' '.join(window_contents)
    # Call the API to translate the contents
    contents_translated = []
    for i, content in enumerate(contents):
        print(f"Translating content {i+1}/{len(contents)}:")
        if i >= WINDOW_SIZE:
            window_contents = contents[i-WINDOW_SIZE:i]
            window_contents_str = ' '.join(window_contents)
        window_contents_str = window_contents_str.replace('\n', ' ')
        call_contents = f"你是一名翻译专家。请保留原文的思想内涵和语义逻辑，使用地道流畅简洁的语言表达，可以意译，避免生硬翻译。人名和地名等专有名词不要翻译。{user_prompt}。这是前文，翻译结果中不要包含它的翻译：{window_contents_str}。请将下面这句英文翻译为中文，请直接告诉我翻译结果，不要添加任何补充说明。：{content}"
        print(f"Call contents: {call_contents}")
        # Call the API to translate the content
        response = client.chat.completions.create(
            model="glm-4",  # model name
            messages=[
                {"role": "user", "content": call_contents,}
            ],
        )
        
        content_translated = response.choices[0].message.content
        ratio = len(content_translated)/len(content.split())
        if '\n' in content_translated:
            print(f"    Response contains multiple lines. Please check the response.")
        if ratio > 2.4:
            print(f"    Response is longer than expected. Please check the response.")
        contents_translated.append(content_translated)
        print(f"    Original: {content}")
        print(f"    Translated: {contents_translated[-1]}")
        print(f"    en ch ratio: {ratio}")
        num_tokens += response.usage.total_tokens

    contents_translated = [i.strip() for i in contents_translated]
    
    return contents_translated, num_tokens
        


def translator(content_path, output_dir, api_key, user_prompt=''):
    WINDOW_SIZE = 2
    MAX_LINE_LENGTH = 80
    
    all_contents = get_content(content_path, MAX_LINE_LENGTH)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Write the content to a file
    output_file = os.path.join(output_dir, "en.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for content in all_contents:
            f.write(content + '\n')

    # ZhipuAI API
    client = ZhipuAI(api_key=api_key) # replace with your own API key
    tot_tokens = 0
    all_contents_translated = []
    all_contents_translated, tot_tokens = translate_all(all_contents, client, user_prompt, WINDOW_SIZE)

    # Write the translated content to a file
    output_file = os.path.join(output_dir, "ch.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for content in all_contents_translated:
            f.write(content + '\n')
    print(f"Translated content written to {output_file}")
    print(f"Total tokens used: {tot_tokens}")


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Translate the content")
    parser.add_argument("--content_path", help="Path to the content file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--user_prompt", help="User prompt")
    parser.add_argument("--api_key", help="API key", required=True)
    args = parser.parse_args()

    content_path = args.content_path
    output_dir = args.output_dir
    user_prompt = args.user_prompt
    api_key = args.api_key

    if user_prompt is None:
        user_prompt = ''

    # Translate the content
    translator(content_path, output_dir, api_key, user_prompt)