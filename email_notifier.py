import smtplib
from email.message import EmailMessage

from settings import SmtpSettings


class EmailNotifier:

    def __init__(self, smtpSettings: SmtpSettings):
        self._smtpSettings = smtpSettings

    def send_alert(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._smtpSettings.sender_email
        msg["To"] = ", ".join(self._smtpSettings.recipients)
        msg.set_content(body)

        with smtplib.SMTP(self._smtpSettings.smtp_server, self._smtpSettings.smtp_port) as server:
            server.starttls()
            server.login(self._smtpSettings.sender_email, self._smtpSettings.sender_password)
            server.send_message(msg)
