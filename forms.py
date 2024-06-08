from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField
from wtforms.validators import DataRequired, URL

class Adbanner(FlaskForm):
    adbookimage = StringField("Ad Image URL", validators=[DataRequired(), URL()])
    adbookname = StringField("Ad Book Name", validators=[DataRequired()])
    submit = SubmitField("Submit Banner")

class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")