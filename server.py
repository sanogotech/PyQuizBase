"""Flask server for code website."""

from jinja2 import StrictUndefined

from flask import Flask, session, flash, request, render_template, redirect
from flask_debugtoolbar import DebugToolbarExtension

# import classes from model module
from model import User, Level, Module, Function

# import database necessities from model module
from model import db, connect_to_db

from questions import ask_question


app = Flask(__name__)

# necessary for using Flask sessions and debug toolbar
app.secret_key = "code"

# forces an error to be raised if variable is undefined in Jinja2
app.jinja_env.undefined = StrictUndefined



@app.route('/')
def show_homepage():
    """Display homepage"""

    # for developing/testing purposes:
    print session

    return render_template("homepage.html")


@app.route("/register", methods=['GET'])
def show_register_form():
    """Displays registration form."""

    return render_template("register.html")


@app.route("/register", methods=['POST'])
def register_user():
    """Registers user."""

    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("firstname")
    last_name = request.form.get("lastname")
    email = request.form.get("email")

    if User.query.filter_by(username=username).first():
        flash("Username is already in use. Please choose a different one.")
    else:
        user = User(username=username, 
                    password=password, 
                    first_name=first_name, 
                    last_name=last_name, 
                    email=email)

        db.session.add(user)
        db.session.flush()

        level = Level(user_id=user.user_id)

        db.session.add(level)
        db.session.commit()

        flash("You have registered as {}.".format(username))

    return render_template("homepage.html")


@app.route("/login", methods=["GET"])
def show_login():
    """Show login page"""

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    """Login"""

    username = request.form.get("username")
    password = request.form.get("password")

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session["current_user"] = username
        flash("Welcome. You are logged in as {}".format(username))
        
        # shows percentage of progress towards next level
        remainder = user.levels.points % 5 
        progress = remainder * 100 / 5
        session["progress"] = progress
    else:
        flash("Username or password does not match. Please try again.")

    return redirect("/{}/dashboard".format(username))


@app.route("/logout")
def logout():
    """Logout user"""

    if "current_user" in session:
        del session["current_user"]

    flash("You are logged out.")
    return redirect("/")


def verify_user(username):
    """Verify user login"""

    if ("current_user" in session and session["current_user"] == username) == True:
        return True
    else:
        flash("Please login.")
        return False
           
        
@app.route("/<username>/dashboard")
def show_dashboard(username):
    """Show student dashboard"""

    if not verify_user(username):
        return redirect("/login")
    
    return render_template("dashboard.html", username=session["current_user"])


@app.route("/<username>/info")
def show_user_info(username):
    """Show user info"""

    if not verify_user(username):
        return redirect("/login")

    user = User.query.filter_by(username=username).first()
    return render_template("user_info.html",
                        user=user)


@app.route("/<username>/studynotes")
def show_study_notes(username):
    """Show study notes"""
    
    if not verify_user(username):
        return redirect("/login")

    study_table = db.session.query(Module).all()
    empty_mod = [ mod.module_id for mod in study_table if mod.functions == [] ]

    return render_template("study_notes.html", 
                            study_table=study_table, 
                            username=username,
                            empty_mod=empty_mod)


@app.route("/<username>/addmodules", methods=["GET"])
def show_add_modules(username):
    """Display add modules page"""

    # currently only handles basic adding of info

    if not verify_user(username):
        return redirect("/login")

    return render_template("add_modules.html", username=username)


@app.route("/<username>/addmodules", methods=["POST"])
def add_modules(username):
    """Add function/module information"""

    mname = request.form.get("mname")
    mdesc = request.form.get("mdesc")
    fname = request.form.get("fname")
    fdesc = request.form.get("fdesc")
    samplecode = request.form.get("samplecode")
    output = request.form.get("output")

    # fetch user to get user_id
    user = User.query.filter_by(username=username).first()

    module = Module(name=mname,
                    description=mdesc,
                    user_id=user.user_id)

    db.session.add(module)
    db.session.commit()   

    function = Function(name=fname, 
                        description=fdesc, 
                        sample_code=samplecode, 
                        output=output,
                        user_id=user.user_id,
                        module_id=module.module_id)

    db.session.add(function)
    db.session.commit()

    flash("Your notes have been added.")

    return redirect("/{}/studynotes".format(username))


@app.route("/<username>/quiz", methods=["GET"])
def show_question(username):
    """Displays question to answer"""

    if not verify_user(username):
        return redirect("/login")

    # chooses a function entry and asks a question
    question, input_code, answer, answer_choices = ask_question()
    session["answer"] = answer
    session["answer_choices"] = answer_choices

    # print "session answer:", session["answer"]
    # print answer_choices

    return render_template("question.html", 
                            question=question, 
                            input_code=input_code, 
                            answer_choices=enumerate(answer_choices))


@app.route("/<username>/quiz", methods=["POST"])
def process_question(username):
    """Processes student answer and displays results with answer."""

    user_answer = request.form.get("useranswer")

    # print "user_answer:", user_answer
    
    # User answer is passed back from the form as a number corresponding 
    # to the index of the list of answers.
    if session["answer_choices"][int(user_answer)] == session["answer"]:
        result = "correct!"
        user = User.query.filter_by(username=session["current_user"]).first()
        user.levels.points += 1
        if user.levels.points % 5 == 0:
            user.levels.level = user.levels.points/5
            flash("CONGRATULATIONS!!! You've reached level {}".format(user.levels.level))
        db.session.commit()
        # print user.levels.points 

        remainder = user.levels.points % 5 
        progress = remainder * 100 / 5
        session["progress"] = progress

    else:
        result = "wrong. Don't give up. Keep studying, and you'll get it right next time!"

    return render_template("answer.html", result=result, answer=session["answer"])






if __name__ == "__main__":

    # for debugging
    app.debug = True
    app.jinja_env.auto_reload = app.debug

    connect_to_db(app)

    # Use DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
