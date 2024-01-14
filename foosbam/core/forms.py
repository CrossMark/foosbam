from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, SubmitField, TimeField
from wtforms.validators import InputRequired

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