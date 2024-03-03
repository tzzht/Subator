# What is Subator
**Subator** is a simple bilingual srt subtitle production tool. The tool comprises five core modules, implementing functions for downloading, transcribing, translating, segmenting, and aligning.
- Downloader: Utilizes the pytube package to download video and audio streams from YouTube.
- Transcriber: Employs WhisperX for speech recognition on audio streams, providing word-level timestamps.
- Translator: Uses llm(qwen-max, glm-4) for translating sentences one by one.
- Spliter: Utilizes spaCy to segment sentences into short fragments, with Chinese not exceeding 33 characters and English not exceeding 80 letters.
- Aligner: Reads the word-level timestamps from WhisperX, aligns fragmens, and utilizes the srt package to output subtitles.
# Prerequisites
- (optional) miniconda
    - https://docs.anaconda.com/free/miniconda/miniconda-install/
- pytube
    - `pip install pytube`
-  WhisperX
    - https://github.com/m-bain/whisperX
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
`python .\src\main.py --url "https://www.youtube.com/videoxxxxx" --save_dir path\to\save\directory --model_path .\models\ --api_key_path .\api_key.txt > subator.log`
# Some Points to Note
- Recommend using qwen-max. Because its translation performance is better than glm-4, and glm-4 often errors due to sensitive information censorship.
- WhisperX sometimes generates incorrect timestamps. After transcription is completed in the transcriber, please use video playback tools such as PotPlayer to open save_dir\video_author\video_title\resources\audio.webm and check if the English subtitle timings correspond correctly.
- WhisperX does not provide timestamps for numbers and special characters. If the video contains a lot of numbers, Subator's performance will be poor.
- llm sometimes provides incorrect translations. After translation is completed in the translator, search for "Please check the response" in the subator.log file, locate the potentially erroneous lines, and then modify the corresponding lines in save_dir\video_author\video_title\resources\ch.txt. ***Do not modify en.txt***, otherwise it won't match with the word-level timestamp. Make sure ch.txt and en.txt have the same number of lines.
- The effectiveness of the spliter is not very ideal. Before translation in the translator, manually divide overly long sentences (more than 240 characters) into multiple lines in audio.txt to improve the effectiveness.
- ***Subator can only help reduce the time it takes to create subtitles. The generated subtitles need to be proofread using tools like PR or SubtitleEdit before use.***