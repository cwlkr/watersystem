from flask import Flask, render_template, jsonify, request, redirect, flash
import glob
from flask_socketio import SocketIO, emit
import atexit
from pump_utils import Pump, PumpObserver, ProtectedPumpSwitch, cleanGPIO, WaterLevelSensor, SwitchObserver
import crontab_utils
from config_loader import load_config
from flask_login import login_required, LoginManager, current_user, UserMixin, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import  DataRequired
from flask_wtf import FlaskForm

hash = generate_password_hash('penguinM3:=11')
USERS={'cedric': hash}

def get_user(username):
    if not username in USERS:
        return None
    else:
        return User(username, USERS.get(username))

class User(UserMixin):
    def __init__(self, user_name, pw_hash):
        self.username = user_name
        self.id = self.username
        self.pw_hash = pw_hash
        super(User).__init__()
        
    def check_password(self, form_pw):
        return check_password_hash(self.pw_hash, form_pw)
    
def secret_code():
    # if exitsts:
    #    load
    # else:
    #    generate and save
    return 'secret!'

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_code()
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

config = load_config(debug=app.config['DEBUG'])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user(form.username.data.lower())
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect("/login")
        login_user(user, remember=form.remember_me.data)
        return redirect("/")
    return render_template('login.html', title='Sign In', form=form)
    

@app.route('/get_log_data')
def get_log_data():
    # if slow make sure to only load parts.. jsonify?
    log_files = sorted(glob.glob('watersys*.log*'))
    a = []
    for f in log_files:
        with open(f) as file:
            a.extend(file.read().splitlines()[::-1])
    return jsonify(a)

@app.route('/get_pump_status')
def get_pump_status():
    return jsonify(pump.is_running) # str(pump_running)

@app.route('/get_waterlvl')
def get_waterlvl():
    return jsonify(waterlvl_sensor.check_water_with_delay())

@app.route('/')
@login_required
def hello():
    return render_template('index.html')

@app.route('/cron_jobs')
def get_cron_jobs():
    return jsonify(cronhandler.get_cron_jobs(silent=True))

@app.route('/change_job_active', methods=["POST"])
@login_required
def edit_cron_active():
    if request.method == 'POST':
        cronhandler.set_enable_job(request.form.get('idx'), request.form.get('checked'))
    return '200'
    
@app.route('/add_cron_job', methods=["POST"])
@login_required
def add_cron_job():
    if request.method == 'POST':
        return cronhandler.set_cron_job(request.form)
    return 'n'

@socketio.on('pump_switch_press')
def pump_flip_switch():
    """
    Do something on button press.
    """
    pump_controller.flip_switch()
    return 'nothing'

@socketio.on('switch_pump_on_with_timeout')
def switch_pump_on(x=None):
    if x is None:
        return {'timed':0}
    else:
        return {'timed': pump_controller.switch_on_with_timout(x)}

@app.route('/logout')
def logout():
    logout_user()
    return redirect("/")

@socketio.on('connect')
def handle_connect():
    # Handle client connection
    print('Client connected')
    # Perform necessary actions

@app.route('/pump_time_out')
def get_time_out_value():
    return jsonify(config["PUMP_CONTROL"]["MAX_TIME_ON"])

@atexit.register
def cleanup_handler():
    with cleanGPIO():
        pump.stop()
pump = Pump(config["PUMP_CONTROL"]["RELAIS_1_GPIO"], debug=config["DEBUG_MODE"])
pump.register(PumpObserver(app))
pump_controller = ProtectedPumpSwitch(pump, max_time_on=config["PUMP_CONTROL"]["MAX_TIME_ON"])
cronhandler = crontab_utils.CronTabHandler(user=config["CRONTAB"]["USER"])
cronhandler.register(crontab_utils.CronObserver(app))
waterlvl_sensor = WaterLevelSensor(
                                   config["WATER_SENSOR"]["IN_GPIO_W"],
                                   config["WATER_SENSOR"]["OUT_GPIO_W"],
                                   config["WATER_SENSOR"]["WATERLVL_VALUE"],
                                   config['DEBUG_MODE']
                                   )
pump_controller.register(SwitchObserver(waterlvl_sensor, app))

# add if main
if __name__ == '__main__':
    socketio.run(app)

