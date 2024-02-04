from flask import render_template
from flask_mail import Message
from foosbam import mail

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

def send_password_reset(user):
    token = user.get_reset_password_token()
    send_email('[Foosbam] Password Reset',
        sender='foosbam@gmail.com',
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )