# What is Subator
**Subator** is a simple bilingual srt subtitle production tool. The tool comprises five core modules, implementing functions for downloading, transcribing, translating, segmenting, and aligning.

- Downloader: Utilizes the pytube package to download video and audio streams from YouTube.
- Transcriber: Employs WhisperX for speech recognition on audio streams, providing word-level timestamps. Utilizes fullstop-deep-punctuation-prediction for sentence segmentation, 
- Translator: Uses llm(qwen-max, glm-4) for translating sentences one by one.
- Spliter: Utilizes spaCy to segment sentences into short fragments, with Chinese not exceeding 33 characters and English not exceeding 80 letters.
- Aligner: Reads the word-level timestamps, aligns fragmens, and utilizes the srt package to output subtitles.

# Prerequisites
- (optional) miniconda
    - https://docs.anaconda.com/free/miniconda/miniconda-install/
- pytubefix
    - `pip install pytubefix`
- WhisperX
    - https://github.com/m-bain/whisperX
- fullstop-deep-punctuation-prediction
    - https://github.com/oliverguhr/fullstop-deep-punctuation-prediction
- zhipuai
    - https://open.bigmodel.cn/dev/api
- dashscope
    - https://help.aliyun.com/zh/dashscope/developer-reference/
- spaCy
    - https://spacy.io/usage
    - `conda install -c conda-forge spacy`
    - `python -m spacy download zh_core_web_trf`
    - `python -m spacy download en_core_web_trf`
- srt
    - `pip install -U srt`
- webm
    - https://www.fnordware.com/WebM/
    
# Getting Started
`python .\src\main.py --url "https://www.youtube.com/videoxxxxx" --save_dir path\to\save\directory --api_key_path .\api_key.txt`

- If you are using `main.py`, Subator will create a `save_dir\video_author\video_title\resources` folder in `save_dir`. 

- The downloader will download video and audio streams to `resources\video.webm` and `resources\audio.webm`. 

- The transcriber will transcribe `resources\audio.webm` and segment it with fullstop-deep-punctuation-prediction. Then output the results to `resources\`. Other modules will use two files: `timestamps.json` containing word-level timestamps, `sentences.txt` containing transcription sentences. Before translation, please ensure correct timestamps by checking with Potplayer. Just open the audio.webm, and check whether the timestamps of `audio.srt` is correct.

- The translator will read text from `sentences.txt`, and use the LLM interface for translation. This may take some time (qwen throttles to 80 calls per minute). Translation results will be saved in `sentences_translated.txt`, it has corresponding lines with `sentences.txt`. LLM outputs may sometimes deviate from expectations (containing context, additional explanatory statements, multiple lines, error due to safety checks, etc.). After translation, search for `'Please check the response.'` in `translator.log` to locate potential errors and modify the corresponding lines in `sentences_translated.txt`. Do not modify `sentences.txt` as its content corresponds to word-level timestamps. 

- The spliter will read `sentences.txt` and `sentences_translated.txt`, then split sentences into smaller fragments using simple strategies and spaCy. Results will be saved in `fragments.json`. 

- The aligner will read `fragments.json` and `timestamps.json` to generate the final subtitle file, which will be saved in the `save_dir\video_author\video_title` folder.

# Some Points to Note
- Recommend using `qwen-max`. Because its translation performance is better than `glm-4`, and `glm-4` often errors due to sensitive information censorship.
- WhisperX does not provide timestamps for numbers and special characters. If the video contains a lot of numbers, Subator's performance will be poor.
- ***Subator can only help reduce the time it takes to create subtitles. The generated subtitles need to be proofread using tools like PR or SubtitleEdit before use.***