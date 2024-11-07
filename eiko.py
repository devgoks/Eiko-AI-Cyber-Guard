from flask import Flask, render_template, request
from openai import OpenAI
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import logging
import uuid
import hashlib
import json
from ipaddress import ip_address
from urllib.parse import urlparse

load_dotenv()

# Set your OpenAI API key
openai_api_key = os.environ.get('OPENAPI_SECRET_KEY')
client = OpenAI(api_key=openai_api_key)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

app = Flask(__name__)

# New helper functions
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

def validate_ip(ip):
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False

def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

# Existing code
def check_fraudulent_message(message):
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

        chatgpt_advice, gemini_advice = check_fraudulent_message(message)

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=False)
