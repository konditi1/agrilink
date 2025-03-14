from celery import shared_task
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings


@shared_task
def send_email(recipient, subject, body):
    """
    Sends an email to the specified recipient with the given subject and body.

    Parameters:
    recipient (str): The email address of the recipient.
    subject (str): The subject of the email.
    body (str): The body content of the email.

    This function constructs an email message using the provided subject and body,
    and sends it to the recipient's email address using the SMTP server configured
    in the Django settings. It handles exceptions during the email sending process
    and prints a success or failure message accordingly.
    """

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        if settings.EMAIL_USE_TLS:
            server.starttls()
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"Email sent successfully to {recipient}")

    except Exception as e:
        print(f"Failed to send email: {e}")

@shared_task
def send_order_confirmation_email(order_id, buyer_email):
    """
    Send an order confirmation email to the buyer.
    """
    subject = "Order Confirmation from Agrilink"
    body = f"Your order with ID {order_id} has been received and is being processed. Thank you for shopping with us!"

    send_email(buyer_email, subject, body)
    return f"Email sent to {buyer_email} for Order ID {order_id}"
