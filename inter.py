from openai import OpenAI
import speech_recognition as sr
import keyboard
import pyttsx3
import os
from dotenv import load_dotenv

load_dotenv()

# Configure OpenAI API
openai_api_key = os.environ.get('OPENAPI_SECRET_KEY')
client = OpenAI(api_key=openai_api_key)

def transcribe_audio_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening... Press SPACE again to stop.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"Transcribed Text: {text}")
            return text
        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError as e:
            print(f"Error with the speech recognition service: {e}")
    return None

def generate_response(prompt):
    try:
        # response = openai.Completion.create(
        #     engine="text-davinci-003",
        #     prompt=prompt,
        #     max_tokens=150,
        #     temperature=0.7
        # )
        # answer = response.choices[0].text.strip()

        messages = [
            {"role": "system", "content": "You are a technical cyber guard, So check if the conversation is fraudulent"},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )

        answer = response.choices[0].message.content
        print(f"GPT-3 Response: {answer}")
        return answer
    except Exception as e:
        print(f"Error generating response: {e}")
    return None

def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def assistant():
    is_recording = False

    print("Press SPACE to start recording...")
    while True:
        if keyboard.is_pressed("space") and not is_recording:
            # Start recording
            is_recording = True
            print("Recording started. Press SPACE to stop.")
            audio_text = transcribe_audio_to_text()
            if audio_text:
                answer = generate_response(audio_text)
                # if answer:
                #     speak_text(answer)
            is_recording = False
            print("Recording stopped. Press SPACE to start again.")

if __name__ == "__main__":
    assistant()
