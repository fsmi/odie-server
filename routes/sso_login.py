#! /usr/bin/env python3

# routes that are only needed for local servers, as production servers usually have their
# own login pages we redirect to. Everything you add to this file will only get imported
# if config.LOCAL_SERVER is True.

import datetime
import uuid
import urllib.parse

from api_utils import handle_client_errors
from flask import request, redirect
from flask.ext.login import current_user, login_user, login_required, logout_user
from odie import app, csrf, sqla
from db.fsmi import User, Cookie

login_page_text = """<html>
<body>
<h1>Login</h1>
<form action="/login?next=%s" method='post'>
  <input name='username' placeholder="Username"/>
  <input name='password' placeholder="Password" type='password'/>
  <button type='submit'>Login</button>
</form>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login_page():
    if request.method == 'GET':
        return login_page_text % urllib.parse.quote_plus(request.args.get('next'))
    user = User.authenticate(request.form['username'], request.form['password'])
    if user:
        # see comment in fsmi.Cookie.refresh as to why we need this in python
        now = datetime.datetime.now()
        cookie = str(uuid.uuid4())
        sqla.session.add(Cookie(sid=cookie, user_id=user.id, last_action=now, lifetime=172800))
        login_user(user)
        sqla.session.commit()
        response = app.make_response(redirect(request.args.get('next')))
        response.set_cookie('FSMISESSID', value=cookie)
        return response
    return 'Nope'


@app.route('/logout')
@handle_client_errors
@login_required
def logout():
    Cookie.query.filter_by(user_id=current_user.id).delete()
    sqla.session.commit()
    response = app.make_response(redirect(request.args.get('next')))
    response.set_cookie('FSMISESSID', value='', expires=0)
    logout_user()
    return response

