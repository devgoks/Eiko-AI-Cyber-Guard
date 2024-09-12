from flask import Flask, render_template, request
from openai import OpenAI

# Set your OpenAI API key
openai_api_key = 'Open ApI key'
client = OpenAI(api_key=openai_api_key)

app = Flask(__name__)

def check_fraudulent_message(message):
    messages = [
        {"role": "system", "content": "Is the following message fraudulent?..., always include an advice in your response.....Also, at the end of your response if fraudulent add hashtag #Fraudulent if not #Nonfraudulent"},
        {"role": "user", "content": message}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    assistant_response = response.choices[0].message.content

    if '#fraudulent' in assistant_response.lower():
        return True, assistant_response
    else:
        return False, assistant_response

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form["user_input"]
        channel = request.form["channel"]
        sender = request.form["sender"]
        time_received = request.form["time_received"]
        message = "channel: " + channel + ", sender: " + sender + ", time_received: " + time_received + ", message: " + user_input
        fraudulent, advice = check_fraudulent_message(message)
        return render_template("result.html", user_input=user_input, fraudulent=fraudulent, advice=advice)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

