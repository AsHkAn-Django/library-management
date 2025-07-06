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

### Tutorial