#! /usr/bin/env python3

import smtplib
from datetime import date
from email.message import EmailMessage

def sendEmail(address, id):
    today = date.today()
    isoFormat = str(today.year) + "-" + str(today.month) + "-" + str(today.day)

    msg = EmailMessage()
    msg['Subject'] = 'ID Protokollkauf vom ' + isoFormat
    msg['From'] = 'odie@fsmi.uni-karlsruhe.de'
    msg['To'] = address

    mail = "Hallo,\n du hast heute Protokolle bei der Fachschaft Mathematik und Informatik am KIT gekauft.\n"
    mail += "Dafür möchten wir uns bei dir bedanken.\n Deine ID, die du für die Rückgabe des Protokolles benötigst, lautet:\n"
    mail += id

    msg.set_content(mail)

    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()
