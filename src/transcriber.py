import argparse
import os
import subator_constants

def transcriber(autdio_path, output_dir, model_path):
    # Create the output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    model = subator_constants.TRANSCRIBE_MODEL
    print_progress = True
    language = subator_constants.TRANSCRIBE_LANGUAGE
    align_model = subator_constants.TRANSCRIBE_ALIGN_MODEL
    # Execute this command line to transcribe the audio file
    command = f"whisperx {autdio_path} --model {model} --print_progress {print_progress} --language {language} --align_model {align_model} --output_dir {output_dir} --model_dir {model_path}"
    print(command)
    os.system(command)


if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Transcribe the audio")
    parser.add_argument("--audio_path", help="Path to the audio file", required=True)
    parser.add_argument("--output_dir", help="Path to the output directory", required=True)
    parser.add_argument("--model_path", help="Path to the model file", required=True)
    args = parser.parse_args()
    
    # Call the transcriber function
    transcriber(args.audio_path, args.output_dir, args.model_path)