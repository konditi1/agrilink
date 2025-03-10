import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import environ

# Initialize environment variables
env = environ.Env()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Get email settings from .env file
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

def send_email(recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = DEFAULT_FROM_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"Email sent successfully to {recipient}")

    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    send_email('konditi1@gmail.com', 'Test Email', 'This is a test email from Agrilink.')
