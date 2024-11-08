from flask import Flask, request, jsonify
from google.cloud import speech, aiplatform
import threading
import io
from flask_socketio import SocketIO, emit
import os
import google.generativeai as genai
from flask import render_template
import logging
import uuid
import hashlib
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import json
from ipaddress import ip_address
from urllib.parse import urlparse
from collections import defaultdict

load_dotenv()

# Set your OpenAI API key
openai_api_key = os.environ.get('OPENAPI_SECRET_KEY')
client = OpenAI(api_key=openai_api_key)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

app = Flask(__name__)

# HashMap to store previous transcriptions
transcription_history = defaultdict(list)

socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Google Cloud Speech and Vertex AI clients
speech_client = speech.SpeechClient()
aiplatform.init()  # Ensure proper authentication setup for Vertex AI

# Endpoint to receive and process audio
@app.route('/process_audio', methods=['POST'])
def process_audio():
    # Get the session ID from the request
    session_id = request.form.get('sessionId')
    if not session_id:
        return jsonify({"message": "Session ID is missing"}), 400

    # Get the audio file from the request
    audio_file = request.files['audio']
    audio_content = audio_file.read()

    # Use Google Speech-to-Text API to transcribe audio
    transcript = transcribe_audio(audio_content)

    if transcript:
        print(f"Transcript: {transcript}")

        # Append transcript to the existing session's history
        transcription_history[session_id].append(transcript)

        print(f"Appended Transcript: {transcription_history[session_id]}")

        # Check if the transcript contains fraudulent content
        check_fraudulent_message(transcription_history[session_id])

    return jsonify({"message": "Audio processed successfully"}), 200


def transcribe_audio(audio_content):
    print(len(audio_content))
    # Configure audio settings for transcription
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code="en-US"
    )

    # Perform the transcription
    try:
        response = speech_client.recognize(config=config, audio=audio)
        print(response)
        transcript = ''.join([result.alternatives[0].transcript for result in response.results])
        return transcript
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def check_fraudulent_message(message):

    message_joined = " ".join(message)

    socketio.emit('successful_transcription', {'transcription': message_joined})


    # Instruction for Google Gemini model
    fraud_check_instruction = (
        "You are checking a transcribed phone call currently ongoing..."
        "check if the following conversation is fraudulent? Always include advice in your response. "
        "At the end of your response, if fraudulent, add hashtag #Fraudulent; if not, #Nonfraudulent."
        "Respond in four lines...well spaced"
    )

    # Initialize Google Gemini model
    google_model = genai.GenerativeModel("gemini-1.5-flash")
    # Generate model response
    google_model_response = google_model.generate_content(f"{fraud_check_instruction}\n Conservation Text to Check:\n{message_joined}")

    # Extract the response text and check for fraud status
    response_text = google_model_response.text.replace('*', '')

    print(response_text)

    if '#Fraudulent' in response_text:
        socketio.emit('fraud_detected', {'message': response_text})


# WebSocket event for testing
@socketio.on('connect')
def handle_connect():
    print("Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@app.route('/eiko-ai-call-guard')
def eiko_ai_call_guard():
    return render_template('index2.html')

def check_fraudulent_message_chat(message):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{current_time} : {message} ")
    fraud_check_instruction = "Is the following message fraudulent?..., always include an advice in your response.....Also, at the end of your response if fraudulent add hashtag #Fraudulent if not #Nonfraudulent"

    messages = [
        {"role": "system", "content": fraud_check_instruction},
        {"role": "user", "content": message}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    chatgpt_assistant_response = response.choices[0].message.content

    google_model = genai.GenerativeModel("gemini-1.5-flash")
    google_model_response = google_model.generate_content(fraud_check_instruction + " \n Text to Check: \n" + message)

    return chatgpt_assistant_response, google_model_response.text.replace('*', '')

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form["user_input"]
        channel = request.form["channel"]
        sender = request.form["sender"]
        time_received = request.form["time_received"]
        message = "channel: " + channel + ", sender: " + sender + ", time_received: " + time_received + ", message: " + user_input

        # Use new utility functions if desired
        request_id = generate_request_id()
        hashed_message = hash_message(user_input)
        log_request(message)

        chatgpt_advice, gemini_advice = check_fraudulent_message_chat(message)

        if '#fraudulent' in chatgpt_advice.lower():
            chatgpt_fraudulent = True
        else:
            chatgpt_fraudulent = False
        if '#fraudulent' in gemini_advice.lower():
            gemini_fraudulent = True
        else:
            gemini_fraudulent = False

        return render_template("result.html", user_input=user_input, gemini_advice=gemini_advice,
                               gemini_fraudulent=gemini_fraudulent,
                               chatgpt_fraudulent=chatgpt_fraudulent, chatgpt_advice=chatgpt_advice,
                               request_id=request_id, hashed_message=hashed_message)
    return render_template("index.html")

def generate_request_id():
    return str(uuid.uuid4())

def hash_message(message):
    return hashlib.sha256(message.encode()).hexdigest()

def log_request(message):
    logging.basicConfig(filename="app.log", level=logging.INFO)
    logging.info(f"{datetime.now()}: Received message - {message}")

def parse_user_agent(user_agent):
    return {
        "browser": user_agent.split('/')[0] if user_agent else "Unknown",
        "os": user_agent.split('/')[1] if len(user_agent.split('/')) > 1 else "Unknown"
    }


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)