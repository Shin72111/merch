from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import  DataRequired, EqualTo
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')



class AdminForm(FlaskForm):
    admin_username = StringField('Admin Username', validators=[DataRequired()])
    admin_password = PasswordField('Admin Password')
    admin_password2 = PasswordField(
        'Repeat Admin Password', validators=[EqualTo('admin_password')])
    member_username = StringField('Member Username', validators=[DataRequired()])
    member_password = PasswordField('Member Password')
    member_password2 = PasswordField(
        'Repeat Member Password', validators=[EqualTo('member_password')])
    submit = SubmitField('Save')
