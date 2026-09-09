import smtplib
from email.message import EmailMessage


class EmailNotifier:

    def __init__(self, config):
        self._config = config

    def send_alert(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._config.sender_email
        msg["To"] = ", ".join(self._config.recipients)
        msg.set_content(body)

        with smtplib.SMTP(self._config.smtp_server, self._config.smtp_port) as server:
            server.starttls()
            server.login(self._config.sender_email, self._config.sender_password)
            server.send_message(msg)
