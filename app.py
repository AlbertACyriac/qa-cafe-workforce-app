from flask import Flask, render_template

app = Flask(__name__)

app.config["SECRET_KEY"] = "dev-secret-key"


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/employees")
def employees():
    sample_employees = [
        {
            "id": 1,
            "name": "Amelia Smith",
            "site": "Manchester Mainline",
            "job_role": "HR Manager",
            "start_date": "2024-01-15",
        },
        {
            "id": 2,
            "name": "Daniel Brown",
            "site": "Liverpool Franchise",
            "job_role": "Site Manager",
            "start_date": "2023-09-01",
        },
    ]

    return render_template("employees.html", employees=sample_employees)


if __name__ == "__main__":
    app.run(debug=True) 