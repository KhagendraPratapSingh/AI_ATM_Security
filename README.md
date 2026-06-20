# AI ATM Security System

## Overview

AI ATM Security System is an intelligent surveillance and security monitoring solution developed for ATM environments. The system uses Artificial Intelligence, Computer Vision, Face Recognition, and Object Detection to detect threats in real time and generate alerts.

The project can identify authorized and unauthorized persons, detect suspicious activities, capture evidence images, maintain security logs, and send instant notifications to security personnel.

---

## Features

### Face Recognition

* Detects and recognizes authorized users.
* Identifies unknown individuals.
* Maintains a database of registered faces.

### Weapon Detection

* Detects weapons using YOLOv8.
* Supports real-time monitoring through camera feeds.
* Captures evidence when a threat is detected.

### Evidence Collection

* Automatically saves screenshots of detected threats.
* Stores evidence images for future investigation.

### Email Alerts

* Sends instant email notifications with evidence images.
* Provides details of detected threats.

### SMS Alerts

* Sends emergency SMS notifications using Twilio.
* Alerts security personnel immediately.

### Threat Logging

* Stores all security events in a SQLite database.
* Maintains timestamps and threat information.

### Web Dashboard

* Built using Flask.
* Provides live monitoring and management interface.

---

## Technologies Used

* Python 3.11
* Flask
* OpenCV
* YOLOv8
* Face Recognition
* NumPy
* SQLite3
* Twilio API
* SMTP Email Service
* HTML
* CSS
* JavaScript

---

## Project Structure

AI_ATM_Security/

├── app.py

├── faces/

├── static/

│   └── evidence/

├── templates/

├── security.db

├── yolov8n.pt

└── README.md

---

## Installation

### Clone Repository

```bash
git clone https://github.com/KhagendraPratapSingh/AI_ATM_Security.git
cd AI_ATM_Security
```

### Create Virtual Environment

```bash
python -m venv venv
```

Activate Environment

Windows:

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

Open browser:

```text
http://127.0.0.1:5000
```

---

## Workflow

1. Camera captures live video feed.
2. Face Recognition identifies individuals.
3. YOLOv8 detects weapons or suspicious objects.
4. Evidence image is captured automatically.
5. Alert is generated.
6. Email and SMS notifications are sent.
7. Event is stored in the database.

---

## Future Enhancements

* Multi-camera support
* Cloud database integration
* Mobile application
* Real-time dashboard analytics
* AI behavior analysis
* Automatic police alert system

---

## Academic Information

### Project Title

AI ATM Security System

### Course

Bachelor of Computer Applications (BCA)

### Developed By

Khagendra Pratap Singh

### Technologies

Python, Flask, OpenCV, YOLOv8, Face Recognition, Twilio, SQLite

---

## License

This project is developed for educational and research purposes.
