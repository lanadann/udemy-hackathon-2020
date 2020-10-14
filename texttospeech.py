from google.cloud import texttospeech as tts


def text_to_wav(text, output_file, voice_name='en-US-Standard-B'):
    language_code = '-'.join(voice_name.split('-')[:2])
    text_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name)
    audio_config = tts.AudioConfig(
        audio_encoding=tts.AudioEncoding.LINEAR16)

    client = tts.TextToSpeechClient()
    response = client.synthesize_speech(
        input=text_input,
        voice=voice_params,
        audio_config=audio_config)

    filename = 'audio_files/{output_file}.wav'.format(output_file=output_file)
    with open(filename, 'wb+') as out:
        out.write(response.audio_content)
        print('Audio content written to "{filename}"'.format(filename=filename))
    return filename