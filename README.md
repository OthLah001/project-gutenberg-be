# Project Gutenber - Backend

This is the **backend** for the Book Analysis project (Project Gutenberd). It provides API endpoints to fetch books, analyze their content using LLMs, and manage user search history.

## Features

✅ Fetch books from **Project Gutenberg**  
✅ Process book content using **Groq's LLM**  
✅ Store and retrieve **text analysis results**  
✅ User authentication (Signup/Login)  
✅ Track **search history**

---

## Installation Guide

### **Clone the Repository**

```bash
git clone https://github.com/OthLah001/project-gutenberg-be.git
cd project-gutenberg-be
```

### **Install PostgreSQL & Python**

Make sure you have:

- **PostgreSQL** (version 12 or later) → [Download Here](https://www.postgresql.org/download/)
- **Python** (version 3.9 or later) → [Download Here](https://www.python.org/downloads/

### **Create a Python Virtual Environment**

```bash
python -m venv env
source env/bin/activate   # On macOS/Linux
env\Scripts\activate      # On Windows
```

### **Install Dependencies**

Make sure you are in the project directory, then install all required packages:

```bash
pip install -r requirements.txt
```

### **Set Up PostgreSQL Database**

- Create a new PostgreSQL database

### Environment Variables

Create a **`config/.env` file** to store your API keys & secrets:

```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=postgres://your_db_user:your_db_password@localhost:5432/your_db_name
GROQ_API_KEY=your_groq_api_key
GROQ_LLM_MODEL=llama-3.3-70b-versatile
REDIS_URL=redis://localhost:6379/0
```

### **Apply Migrations**

```bash
python manage.py migrate
```

### **Run the Django Server**

```bash
python manage.py runserver
```

The backend will be available at **`http://127.0.0.1:8000/`**

## API Documentation

Django Ninja auto-generates API docs.  
Visit **`http://127.0.0.1:8000/api/docs/`** to explore the available endpoints.

---
