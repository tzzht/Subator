import argparse
import os

def transcriber(autdio_path, output_dir, model_path):
    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    model = "large-v3"
    print_progress = True
    language = "en"
    align_model = "WAV2VEC2_ASR_LARGE_LV60K_960H"
    # Execute this command line to transcribe the audio file
    os.system(f"whisperx {autdio_path} --model {model} --print_progress {print_progress} --language {language} --align_model {align_model} --output_dir {output_dir} --model_dir {model_path}")


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Transcribe the audio")
    parser.add_argument("--audio_path", help="Path to the audio file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--model_path", help="Path to the model file", required=True)
    args = parser.parse_args()
    
    # Call the transcriber function
    transcriber(args.audio_path, args.output_dir, args.model_path)