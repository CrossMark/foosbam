from flask_login import current_user
from flask_wtf import FlaskForm
from foosbam import db
from foosbam.models import User
import sqlalchemy as sa
from wtforms import DateField, IntegerField, SelectField, SubmitField, StringField, TimeField
from wtforms.validators import InputRequired, Email, ValidationError

class AddMatchForm(FlaskForm):
    # Match fields
    date = DateField('Date', validators=[InputRequired()])
    time = TimeField('Time', validators=[InputRequired()])
    att_black = SelectField('Team Black - Attacker', validators=[InputRequired()])
    def_black = SelectField('Team Black - Defender', validators=[InputRequired()])
    att_white = SelectField('Team White - Attacker', validators=[InputRequired()])
    def_white = SelectField('Team White - Defender', validators=[InputRequired()])

    # Result fields
    score_black = IntegerField('Team Black - Score', validators=[InputRequired()])
    score_white = IntegerField('Team White - Score', validators=[InputRequired()])
    klinker_att_black = IntegerField('Team Black - Attacker Klinkers', validators=[InputRequired()])
    klinker_def_black = IntegerField('Team Black - Defender Klinkers', validators=[InputRequired()])
    klinker_att_white = IntegerField('Team White - Attacker Klinkers', validators=[InputRequired()])
    klinker_def_white = IntegerField('Team White - Defender Klinkers', validators=[InputRequired()])
    keeper_black = IntegerField('Team Black - Keeper Goals', validators=[InputRequired()])
    keeper_white = IntegerField('Team White - Keeper Goals', validators=[InputRequired()])

    add_result = SubmitField('Add result', name='Add result')
  
    def validate(self, extra_validators=None):
        if not super().validate():
            return False
        
        seen = set()
        for player in [self.att_black, self.def_black, self.att_white, self.def_white]:
            if player.data in seen:
                player.errors.append('Please select four distinct players.')
                return False
            else:
                seen.add(player.data)
        return True
    
class EditProfileForm(FlaskForm):
    username = StringField('Name', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email()])
    submit = SubmitField('Save', name='Save')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data.lower()))
        if (not username.data.lower() == current_user.username) and (user is not None):
            raise ValidationError('Username already in use. Please use a different username.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data.lower()))
        if (not email.data.lower() == current_user.email) and (user is not None):
            raise ValidationError('Email already in use. Please use a different email address.')