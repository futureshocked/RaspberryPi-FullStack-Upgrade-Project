from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

resp_text = "Thanks for the message!"
app = Flask(__name__)

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    resp = MessagingResponse()
    resp.message(resp_text)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)

