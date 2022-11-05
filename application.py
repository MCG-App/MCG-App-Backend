from flask import Flask
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
import firebase_admin
from firebase_admin import auth

app = Flask(__name__)
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

default_app = firebase_admin.initialize_app()
print(default_app.name)


class UserModel(db.Model):
    uid = db.Column(db.String, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String, nullable=False)
    group = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'User(uid={self.uid}, first_name={self.first_name}, last_name={self.last_name}, email={self.email}, ' \
               f'group={self.group}) '


with app.app_context():
    db.create_all()

signup_args = reqparse.RequestParser()
signup_args.add_argument('token', type=str, help='Token is required', required=True)
signup_args.add_argument('first_name', type=str, help='First name is required', required=True)
signup_args.add_argument('last_name', type=str, help='Last name is required', required=True)
signup_args.add_argument('group', type=str, help='Group is required', required=True)

user_args = reqparse.RequestParser()
user_args.add_argument('token', type=str, help='Token is required', required=True)

user_resource_fields = {
    'uid': fields.String,
    'first_name': fields.String,
    'last_name': fields.String,
    'email': fields.String,
    'group': fields.String
}


def get_firebase_user(token):
    try:
        decoded_token = auth.verify_id_token(token)
    except firebase_admin.auth.ExpiredIdTokenError:
        abort(403, message='The provided token is expired')
        return
    except firebase_admin.auth.InvalidIdTokenError:
        abort(403, message='The provided token is invalid')
        return
    except firebase_admin.auth.InsufficientPermissionError:
        abort(403, message='The provided token lacks required permissions')
        return

    print(decoded_token)  # debug
    return decoded_token


class User(Resource):
    @marshal_with(user_resource_fields)
    def post(self):
        args = signup_args.parse_args()
        print(args)  # debug
        firebase_user = get_firebase_user(args['token'])

        result = UserModel.query.get(firebase_user['uid'])
        if result:
            abort(409, message='This user already exists')

        user = UserModel(uid=firebase_user['uid'], first_name=args['first_name'], last_name=args['last_name'],
                         email=firebase_user['email'], group=args['group'])

        db.session.add(user)
        db.session.commit()
        return user, 201

    @marshal_with(user_resource_fields)
    def get(self):
        args = user_args.parse_args()
        print(args)  # debug

        firebase_user = get_firebase_user(args['token'])

        user = UserModel.query.get_or_404(firebase_user['uid'], description='This user does not exist')
        print(user)  # debug
        return user, 200


api.add_resource(User, '/user')

if __name__ == '__main__':
    app.run(debug=True)
