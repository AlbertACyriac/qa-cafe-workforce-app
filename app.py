from datetime import date
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# Secret key used by Flask.
# This is suitable only for the local university prototype.
app.config["SECRET_KEY"] = "dev-secret-key"

# Configure the SQLite database.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///workforce.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect SQLAlchemy to the Flask application.
db = SQLAlchemy(app)


class Site(db.Model):
    """Represents a fictional QA Café location."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    site_type = db.Column(db.String(50), nullable=False)

    # One site can contain many employees.
    employees = db.relationship(
        "Employee",
        backref="site",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Site {self.name}>"

class User(db.Model):
    """Represents an authorised QA Café application user."""

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
    )

    site_id = db.Column(
        db.Integer,
        db.ForeignKey("site.id"),
        nullable=True,
    )

    site = db.relationship(
        "Site",
        backref="users",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Employee(db.Model):
    """Represents an employee working at a QA Café site."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    holiday_allowance = db.Column(db.Integer, nullable=False, default=25)

    # Connects each employee to one site.
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("site.id"),
        nullable=False,
    )

    def __repr__(self):
        return f"<Employee {self.name}>"

def login_required(view_function):
    """Require a user to be signed in before accessing a route."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "error")
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.session.execute(
            db.select(User).where(
                User.username == username
            )
        ).scalars().first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role
        session["site_id"] = user.site_id

        flash(
            f"Welcome, {user.username}.",
            "success",
        )

        return redirect(url_for("employees"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/employees")
@login_required
def employees():
    if session.get("role") == "Admin":
        employee_records = db.session.execute(
            db.select(Employee).order_by(Employee.name)
        ).scalars().all()
    else:
        employee_records = db.session.execute(
            db.select(Employee)
            .where(Employee.site_id == session.get("site_id"))
            .order_by(Employee.name)
        ).scalars().all()

    return render_template(
        "employees.html",
        employees=employee_records,
    )

@app.route("/employees/add", methods=["GET", "POST"])
@login_required
def add_employee():
    if session.get("role") == "Admin":
        sites = db.session.execute(
            db.select(Site).order_by(Site.name)
        ).scalars().all()
    else:
        sites = db.session.execute(
            db.select(Site).where(
                Site.id == session.get("site_id")
            )
        ).scalars().all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        start_date_text = request.form.get("start_date", "").strip()
        job_role = request.form.get("job_role", "").strip()
        holiday_allowance_text = request.form.get(
            "holiday_allowance", ""
        ).strip()
        site_id_text = request.form.get("site_id", "").strip()

        errors = []

        if not name:
            errors.append("Employee name is required.")

        if not job_role:
            errors.append("Job role is required.")

        if not start_date_text:
            errors.append("Start date is required.")

        try:
            holiday_allowance = int(holiday_allowance_text)

            if holiday_allowance < 0 or holiday_allowance > 40:
                errors.append(
                    "Holiday allowance must be between 0 and 40 days."
                )
        except ValueError:
            holiday_allowance = None
            errors.append("Holiday allowance must be a whole number.")

        try:
            site_id = int(site_id_text)
        except ValueError:
            site_id = None
            errors.append("A valid site must be selected.")

        selected_site = None

        if site_id is not None:
            selected_site = db.session.get(Site, site_id)

            if selected_site is None:
                errors.append("The selected site does not exist.")

        try:
            employee_start_date = date.fromisoformat(start_date_text)
        except ValueError:
            employee_start_date = None

            if start_date_text:
                errors.append("Start date must be a valid date.")

        if errors:
            for error in errors:
                flash(error, "error")

            return render_template(
                "add_employee.html",
                sites=sites,
            )

        new_employee = Employee(
            name=name,
            start_date=employee_start_date,
            job_role=job_role,
            holiday_allowance=holiday_allowance,
            site_id=selected_site.id,
        )

        db.session.add(new_employee)
        db.session.commit()

        flash("Employee added successfully.", "success")

        return redirect(url_for("employees"))

    return render_template(
        "add_employee.html",
        sites=sites,
    )

@app.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id):
    employee = db.session.get(Employee, employee_id)

    if employee is None:
        return "Employee not found", 404

    if (
        session.get("role") != "Admin"
        and employee.site_id != session.get("site_id")
    ):
        flash(
            "You are not authorised to edit that employee.",
            "error",
        )
        return redirect(url_for("employees"))

    if session.get("role") == "Admin":
        sites = db.session.execute(
            db.select(Site).order_by(Site.name)
        ).scalars().all()
    else:
        sites = db.session.execute(
            db.select(Site).where(
                Site.id == session.get("site_id")
            )
        ).scalars().all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        start_date_text = request.form.get("start_date", "").strip()
        job_role = request.form.get("job_role", "").strip()
        holiday_allowance_text = request.form.get(
            "holiday_allowance", ""
        ).strip()
        site_id_text = request.form.get("site_id", "").strip()

        errors = []

        if not name:
            errors.append("Employee name is required.")

        if not job_role:
            errors.append("Job role is required.")

        if not start_date_text:
            errors.append("Start date is required.")

        try:
            holiday_allowance = int(holiday_allowance_text)

            if holiday_allowance < 0 or holiday_allowance > 40:
                errors.append(
                    "Holiday allowance must be between 0 and 40 days."
                )
        except ValueError:
            holiday_allowance = None
            errors.append("Holiday allowance must be a whole number.")

        try:
            site_id = int(site_id_text)
        except ValueError:
            site_id = None
            errors.append("A valid site must be selected.")

        selected_site = None

        if site_id is not None:
            selected_site = db.session.get(Site, site_id)

            if selected_site is None:
                errors.append("The selected site does not exist.")

        try:
            employee_start_date = date.fromisoformat(start_date_text)
        except ValueError:
            employee_start_date = None

            if start_date_text:
                errors.append("Start date must be a valid date.")

        if errors:
            for error in errors:
                flash(error, "error")

            return render_template(
                "edit_employee.html",
                employee=employee,
                sites=sites,
            )

        employee.name = name
        employee.start_date = employee_start_date
        employee.job_role = job_role
        employee.holiday_allowance = holiday_allowance
        employee.site_id = selected_site.id

        db.session.commit()

        flash("Employee updated successfully.", "success")

        return redirect(url_for("employees"))

    return render_template(
        "edit_employee.html",
        employee=employee,
        sites=sites,
    )
@app.route("/employees/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id):
    employee = db.session.get(Employee, employee_id)

    if employee is None:
        return "Employee not found", 404

    if (
        session.get("role") != "Admin"
        and employee.site_id != session.get("site_id")
    ):
        flash(
            "You are not authorised to delete that employee.",
            "error",
        )
        return redirect(url_for("employees"))

    employee_name = employee.name

    db.session.delete(employee)
    db.session.commit()

    flash(
        f"{employee_name} was deleted successfully.",
        "success",
    )

    return redirect(url_for("employees"))
    
def seed_database():
    """Add fictional sites and employees when the database is empty."""

    existing_site = db.session.execute(
        db.select(Site)
    ).scalars().first()

    if existing_site is not None:
        return

    manchester = Site(
        name="Manchester Mainline",
        site_type="Mainline",
    )

    liverpool = Site(
        name="Liverpool Franchise",
        site_type="Franchise",
    )

    birmingham = Site(
        name="Birmingham Mainline",
        site_type="Mainline",
    )

    db.session.add_all([
        manchester,
        liverpool,
        birmingham,
    ])

    # Save sites first so they receive database IDs.
    db.session.commit()

    employees_to_add = [
        Employee(
            name="Amelia Smith",
            start_date=date(2024, 1, 15),
            job_role="HR Manager",
            holiday_allowance=25,
            site_id=manchester.id,
        ),
        Employee(
            name="Daniel Brown",
            start_date=date(2023, 9, 1),
            job_role="Site Manager",
            holiday_allowance=28,
            site_id=liverpool.id,
        ),
        Employee(
            name="Grace Wilson",
            start_date=date(2025, 2, 10),
            job_role="Barista",
            holiday_allowance=25,
            site_id=manchester.id,
        ),
        Employee(
            name="Noah Taylor",
            start_date=date(2024, 7, 8),
            job_role="Team Leader",
            holiday_allowance=26,
            site_id=birmingham.id,
        ),
        Employee(
            name="Olivia Jones",
            start_date=date(2025, 3, 3),
            job_role="Barista",
            holiday_allowance=25,
            site_id=liverpool.id,
        ),
        Employee(
            name="Ethan Davis",
            start_date=date(2023, 11, 20),
            job_role="Assistant Manager",
            holiday_allowance=27,
            site_id=birmingham.id,
        ),
    ]

    db.session.add_all(employees_to_add)
    db.session.commit()

def seed_users():
    """Create fictional application users if none exist."""

    existing_user = db.session.execute(
        db.select(User)
    ).scalars().first()

    if existing_user is not None:
        return

    manchester = db.session.execute(
        db.select(Site).where(
            Site.name == "Manchester Mainline"
        )
    ).scalars().first()

    liverpool = db.session.execute(
        db.select(Site).where(
            Site.name == "Liverpool Franchise"
        )
    ).scalars().first()

    admin = User(
        username="admin",
        role="Admin",
        site_id=None,
    )
    admin.set_password("Admin123!")

    manchester_manager = User(
        username="manchester_manager",
        role="Site Manager",
        site_id=manchester.id,
    )
    manchester_manager.set_password("Manager123!")

    liverpool_manager = User(
        username="liverpool_manager",
        role="Site Manager",
        site_id=liverpool.id,
    )
    liverpool_manager.set_password("Manager123!")

    db.session.add_all([
        admin,
        manchester_manager,
        liverpool_manager,
    ])

    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()
        seed_users()

    app.run(debug=True)