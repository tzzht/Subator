MAX_EN_FRAGMENT_LENGTH = 80
MAX_CH_FRAGMENT_LENGTH = 33

# downloder
# the video streams are filtered by the type="video", mime_type="video/webm", res="1080p", progressive=False
# the audio streams are filtered by the type="audio", mime_type="audio/webm", abr="160kbps"
VIDEO_MIME_TYPE = "video/webm"
VIDEO_RES = "1080p"
VIDEO_PROGRESSIVE = False
AUDIO_MIME_TYPE = "audio/webm"
AUDIO_ABR = "160kbps"

# transcriber
TRANSCRIBE_MODEL = "medium.en"

# translator
TRANSLATE_WINDOW_SIZE = 1
TRANSLATE_RETRY_LIMIT = 5
CH_EN_RATIO_LIMIT = 3
PUNCTUATION_MODEL_PATH = ""

# spliter
SPACY_EN_MODEL = "en_core_web_trf"
SPACY_CH_MODEL = "zh_core_web_trf"

# save_dir
SAVE_DIR = "E:\\TranslateVideo"

# LLM
LLM = "gpt"

# API_KEY
QWEN_API_KEY = ""
GLM_API_KEY = ""
GPT_API_KEY = ""