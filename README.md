# Library Management

Just a quick little project I made while practicing Django and backend development.
This is part of my journey as I learn and improve my skills.

---

##  About the Project

This is a basic **Library Management System** built using Django. It includes simple frontend styling with **HTML**, **CSS**, **Bootstrap**, and some **JavaScript**.

The system allows users to borrow and return books. Books are managed with stock tracking and **unique barcodes**, and all borrow-return activity is recorded.

This project is part of my learning process as I transition into backend development, with a strong focus on writing clean, understandable code.

---

##  Features

- Add books with unique barcodes
- Track book stock in real time
- Borrow/return system with timestamped records
- Each user can borrow a single copy of a book until it’s returned
- Simple admin interface to manage books and users

---

## 🛠 Technologies Used

- Python
- Django
- HTML
- CSS
- Bootstrap
- JavaScript

---

## 👨 About Me

Hi, I'm **Ashkan** — a junior Django developer who recently transitioned from teaching English as a second language to learning backend development.
I’m currently focused on improving my skills, building projects, and looking for opportunities to work as a backend developer.

- GitHub: [AsHkAn-Django](https://github.com/AsHkAn-Django)
- LinkedIn: [Ashkan Ahrari](https://www.linkedin.com/in/ashkan-ahrari-146080150)

---

##  How to Use

1. **Clone the repository**
```bash
git clone https://github.com/AsHkAn-Django/library-management.git
cd library-management
```

2. **Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate       # On macOS/Linux
.venv\Scripts\activate          # On Windows
```

3. **Install the dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the server**
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Tutorial Deploying an app on railway with postgres
1. create a project and an app and a postgres inside of railway website
2. create a requirements.txt
```txt
Django==5.2.4
gunicorn==23.0.0
whitenoise==6.6.0
dj-database-url==3.0.1
django-decouple==2.1
psycopg2==2.9.10
```

3. in settings
```python
import dj_database_url

CSRF_TRUSTED_ORIGINS = [config('WEB_URL')]


DATABASES = {
    'default': dj_database_url.config(default=config('DATABASE_URL'))
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

4. in ```.env```
```txt
DEBUG=False
ALLOWED_HOSTS=.onrender.com,127.0.0.1,localhost,library-management1.up.railway.app
SECRET_KEY=
WEB_URL=https://library-management1.up.railway.appclear
DATABASE_URL=<becareful you should use the public one here for local and the main one for internal>
```

5. create a ```runtime.txt``` file
```text
python-3.11
```

6. create a ```Procfile``` file
```
web: gunicorn library_management.wsgi --bind 0.0.0.0:8080
```

7. create a ```railway.json``` file
```json
{
  "build": {
    "builder": "nixpacks"
  },
  "start": {
    "cmd": "gunicorn library_management.wsgi --bind 0.0.0.0:$PORT"
  }
}
```

8. add it to github and push it and deploy
