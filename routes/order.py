#!/usr/bin/env python3

from odie import app, csrf, ClientError
from db.userHash import userHash, ToManyAttempts


@app.route('api/orders', methods='POST')
@csrf.exempt
def submit_order():
	uh = userHash()
	try:
		rand = uh.returnIdCard()
	except ToManyAttempts:
		ClientError('to many used tokens generated, please write an email to odie@fsmi.uka.de', status=500)

	print('success')