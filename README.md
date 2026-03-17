# Smart Health Record System

A full-stack web application that enables secure storage, management,
and semantic search of patient health records. The system allows
healthcare staff to upload, manage, and retrieve patient records
efficiently using a modern web interface and intelligent search
functionality.

## Features

-   Secure upload and storage of patient health records
-   Semantic search using TF-IDF and cosine similarity
-   CRUD operations for patient records
-   Multi-page React dashboard for easy navigation
-   Backend REST API for data management
-   Efficient record retrieval compared to simple keyword matching

## Tech Stack

### Frontend

-   React.js
-   HTML
-   CSS
-   JavaScript

### Backend

-   Flask
-   Python

### Database

-   SQLite

### Libraries

-   Pandas
-   NumPy
-   Scikit-learn (TF-IDF Vectorizer)

## System Architecture

Frontend (React.js) → REST API (Flask) → Database (SQLite)

The frontend communicates with the Flask backend through RESTful APIs.\
The backend processes requests, manages patient data, and performs
semantic search operations.

## Project Structure

```text
Smart-Health-Record-System/
│
├── frontend/
│   ├── components/
│   ├── pages/
│   └── App.js
│
├── backend/
│   ├── app.py
│   ├── search_engine.py
│   └── database.py
│
├── database/
│   └── health_records.db
│
└── README.md
```

## Installation

### Clone the repository

git clone https://github.com/ChiragMeghani589/Smart-Health-Record-System.git
cd Smart-Health-Record-System

### Install backend dependencies

pip install -r requirements.txt

### Start the Flask server

python app.py

### Start the React frontend

npm install npm start

## Usage

1.  Login to the dashboard\
2.  Upload patient records\
3.  Search records using keywords or medical terms\
4.  View, update, or delete records

The semantic search engine retrieves the most relevant patient records
using TF-IDF based similarity scoring.

## Future Improvements

-   Role-based authentication
-   Integration with Electronic Health Record (EHR) systems
-   Cloud deployment
-   Advanced NLP based search models
-   Patient data encryption

## Author

Chirag Meghani\
GitHub: https://github.com/ChiragMeghani589
