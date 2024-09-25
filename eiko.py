from flask import Flask, render_template, request
from openai import OpenAI
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Set your OpenAI API key
openai_api_key = os.environ.get('OPENAPI_SECRET_KEY')
client = OpenAI(api_key=openai_api_key)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

app = Flask(__name__)

def check_fraudulent_message(message):
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

    print(response)

    google_model = genai.GenerativeModel("gemini-1.5-flash")

    google_model_response = google_model.generate_content(fraud_check_instruction + " \n Text to Check: \n"+message)

    print(google_model_response.text)

    return chatgpt_assistant_response, google_model_response.text

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form["user_input"]
        channel = request.form["channel"]
        sender = request.form["sender"]
        time_received = request.form["time_received"]
        message = "channel: " + channel + ", sender: " + sender + ", time_received: " + time_received + ", message: " + user_input
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
                               chatgpt_fraudulent=chatgpt_fraudulent, chatgpt_advice=chatgpt_advice)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

