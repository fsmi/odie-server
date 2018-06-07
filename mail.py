#! /usr/bin/env python3

from datetime import date
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

def sendEmail(address, id):
    today = date.today()

    mail = "Hallo,\ndu hast heute Protokolle bei der Fachschaft Mathematik und Informatik am KIT gekauft.\n"
    mail += "Dafür möchten wir uns bei dir bedanken.\nDeine ID, die du für die Rückgabe des Protokolles benötigst, lautet:\n"
    mail += id + "\n\n"
    mail += "Dein Protokollverkauf\n"
    mail += "--\n"
    mail += "Fachschaft Mathematik und Informatik\n"
    mail += "Karlsruher Institut für Technologie\n"
    mail += "Am Fasanengarten 5, 76131 Karlsruhe"

    msg = MIMEText(mail, _charset="utf-8")
    msg['Subject'] = 'ID Protokollkauf vom ' + today.isoformat()
    msg['From'] = 'odie@fsmi.uni-karlsruhe.de'
    msg['To'] = address

    p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE, universal_newlines=True)
    p.communicate(msg.as_string())
