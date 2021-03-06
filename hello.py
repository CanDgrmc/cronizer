from flask import Flask, \
    request, \
    render_template,\
    make_response,\
    jsonify,\
    flash,\
    redirect,\
    url_for,\
    session,\
    logging

from flask_restful import Resource,Api,reqparse
from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
import json
import hashlib
import requests
from pytz import timezone
import pytz
import random
import string
from datetime import datetime
import os


app = Flask(__name__)
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://bc21954e9912a0:17e82e87@us-cdbr-iron-east-01.cleardb.net/heroku_5515d55fdb7870a'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.config['MYSQL_HOST'] = 'us-cdbr-iron-east-01.cleardb.net'
#app.config['MYSQL_USER'] = 'bc21954e9912a0'
#app.config['MYSQL_PASSWORD'] = '17e82e87'
#app.config['MYSQL_DB'] = 'heroku_5515d55fdb7870a'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
db = SQLAlchemy(app)



parser = reqparse.RequestParser()

@app.route('/')
def index():

    return 'Nağber Popiş!'



class logMeIn(Resource):
    def post(self):

        parser.add_argument('email')
        parser.add_argument('password')
        userInfo = parser.parse_args()

        if userInfo.email :
            token = validateUser(userInfo.email, userInfo.password)
            if token :
                return {'success': True, 'message': 'Login Successful' ,'token': token},201
            return { 'success': False, 'message': 'Wrong Credentials'},403





api.add_resource(logMeIn,'/login')



class crons(Resource):
    def get(self):
        token = request.headers.get('Token')
        parser.add_argument('project_id')
        parser.add_argument('limit')
        parser.add_argument('offset')
        req = parser.parse_args()
        user = validateToken(token)
        if user:
            crons = Cron.query.filter_by(user_id=user.id,project_id=req['project_id']).limit(req['limit']).offset(req['offset']).all()
            objcrons = []
            for cr in crons:
                objcrons.append({
                    'json': cr.json,
                    'columns': cr.columns,
                    'project_id': req['project_id'],
                    'created_at' : str(cr.created_at),
                    'limit': req['limit'],
                    'total': len(crons)
                });
            return {'success': True, 'crons': objcrons},200
        return token;
    def post(self):
        parser.add_argument('token')
        parser.add_argument('json')
        parser.add_argument('columns')
        parser.add_argument('error_message')
        parser.add_argument('status')
        parser.add_argument('project_id')
        postData = parser.parse_args();


        tz = pytz.timezone('Europe/Istanbul')
        time_now = datetime.now(tz)


        user = validateToken(postData.token)
        if user:
            status = False
            if postData.status == "1":
                status = True
            else:
                sendMail(user.email,postData.error_message)

            cron = Cron(user_id = user.id, json = postData.json, columns = postData.columns,created_at = time_now,status = status )
            db.session.add(cron)
            db.session.commit()
            if cron.id:
                return {'success': True, 'data': cron.json, 'created_at': str(cron.created_at)}, 201

        return {'success': False, 'message': 'Check your post data / credentials'}, 403

api.add_resource(crons, '/push')


class projects(Resource):
    def get(self):
        token = request.headers.get('Token')
        parser.add_argument('limit')
        parser.add_argument('offset')
        req = parser.parse_args()
        user = validateToken(token);
        projects = Project.query.filter_by(user_id = user.id).limit(req['limit']).offset(req['offset']).all();
        objprojects = []
        for pr in projects:
            objprojects.append({
                'id': pr.id,
                'name': pr.name,
                'description': pr.description,
                'created_at': str(pr.created_at),
                'limit': req['limit'],
                'total': len(projects)
            });
        return {'success': True, 'projects': objprojects},200

    def post(self):
        token = request.headers.get('Token')
        parser.add_argument('name')
        parser.add_argument('description')
        req = parser.parse_args()
        user = validateToken(token)

        if user:
            tz = pytz.timezone('Europe/Istanbul')
            time_now = datetime.now(tz)
            project = Project(user_id = user.id,name=req['name'],description=req['description'],created_at=time_now)
            db.session.add(project)
            db.session.commit()

            trans = {
                'id':project.id,
                'name':project.name,
                'description': project.description
            }
            if project.id:
                return {'success': True, 'data': trans, 'created_at': str(project.created_at)}, 201
            return {'success': False, 'error': 'Proje Kaydedilemedi'}, 403


api.add_resource(projects, '/projects')

class refresh_token(Resource):
    def get(self):
        token = request.headers.get('Token')
        parser.add_argument('limit')
        parser.add_argument('offset')
        req = parser.parse_args()
        user = validateToken(token);
        new_token = id_generator(50);
        user.token = new_token;
        db.session.commit()
        return {'success': True, 'token': new_token},200

api.add_resource(refresh_token, '/refresh_token')




def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def validateUser(email,password):
    user = User.query.filter_by(email=email).first()
    if user:
        m = hashlib.sha224(password.encode()).hexdigest()
        if (m == user.password):
            return user.token
        return False

def validateToken(token):
    user = User.query.filter_by(token= token).first()
    return user

def sendMail(to,content):
    key = 'key-44571fbb1ac9be648dfdc1c36618fedc'
    sandbox = 'onlals.at'

    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(sandbox)
    request = requests.post(request_url, auth=('api', key), data={
        'from': 'noreply@onlals.at',
        'to': to,
        'subject': 'Hatalı Cron',
        'html': render_template('mail/send.html',content = content)
    })

    print
    'Status: {0}'.format(request.status_code)
    print
    'Body:   {0}'.format(request.text)

class Cron(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    json = db.Column(db.Text, nullable=False)
    columns = db.Column(db.Text,nullable = True)
    created_at = db.Column(db.TIMESTAMP,nullable=False)
    status = db.Column(db.Boolean,nullable=False)
    project_id = db.Column(db.Integer, nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100),nullable=False)
    password = db.Column(db.String(100),nullable=False)
    email = db.Column(db.String(100),nullable=False)
    token = db.Column(db.Text,nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    name = db.Column(db.String(100),nullable=False)
    description = db.Column(db.Text,nullable=True)
    created_at = db.Column(db.TIMESTAMP, nullable=False)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    if port == 8000:
        app.run(host='127.0.0.1', port=port)
    else:
        app.run(host='0.0.0.0', port=port)
    db.create_all()

