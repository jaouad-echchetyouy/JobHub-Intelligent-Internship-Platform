import logging

from app.notifier import send_email

logging.basicConfig(level=logging.INFO)
ok = send_email("nouranoura.34@gmail.com", "Test JobHub", "<b>Ça marche</b>", "Ça marche")
print("Email envoyé" if ok else "Échec : lis le message ci-dessus")