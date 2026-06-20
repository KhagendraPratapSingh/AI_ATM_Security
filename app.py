from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
import cv2
from ultralytics import YOLO
import datetime
import sqlite3
import pyttsx3
import threading
from twilio.rest import Client
import smtplib
from email.message import EmailMessage
import os
import time
import face_recognition
import numpy as np

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_login'

# --- CONFIGURATION (YOUR CREDENTIALS) ---
TWILIO_SID = "YOUR_TWILIO_SID"
TWILIO_TOKEN = "YOUR_TWILIO_TOKEN"
FROM_NUMBER = "YOUR_TWILIO_NUMBER"
TO_NUMBER = "YOUR_PHONE_NUMBER"

SENDER_EMAIL = "YOUR_EMAIL"
SENDER_PASSWORD = "YOUR_APP_PASSWORD"
RECEIVER_EMAIL = "YOUR_RECEIVER_EMAIL"

# --- VOICE ENGINE ---
def speak(text):
    def run_speech():
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except: pass
    thread = threading.Thread(target=run_speech)
    thread.start()

# --- LOAD FACES ---
print("👤 Loading Face Database...")
known_face_encodings = []
known_face_names = []
try:
    admin_image = face_recognition.load_image_file("faces/admin.jpg")
    admin_encoding = face_recognition.face_encodings(admin_image)[0]
    known_face_encodings.append(admin_encoding)
    known_face_names.append("ADMIN")
    print("✅ Admin Face Loaded!")
except: print("⚠️ Admin face not found.")

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('security.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS threat_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, message TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS asset_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, 
                  object_name TEXT, 
                  person_seen TEXT,
                  image_path TEXT)''')
    conn.commit()
    conn.close()

init_db()

# LOAD MODEL
model = YOLO("yolov8n.pt")
camera = cv2.VideoCapture(0)

# GLOBALS
last_sms_time = None       # Slow Timer (SMS/Email)
last_log_time = None       # Fast Timer (Database/Voice)
loitering_start_time = None
LOITERING_LIMIT = 20
last_welcome_time = None
last_asset_log_time = {}

# --- ALERTS ---
def send_sms_alert(message):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=message, from_=FROM_NUMBER, to=TO_NUMBER)
        print("✅ SMS SENT!") 
    except Exception as e:
        print(f"❌ TWILIO ERROR: {e}")

def send_email_alert(subject, body, photo_path):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg.set_content(body)
        with open(photo_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='jpeg', filename=f.name)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print("✅ EMAIL SENT!")
    except Exception as e:
        print(f"❌ EMAIL ERROR: {e}")

def save_log(msg):
    conn = sqlite3.connect('security.db')
    conn.execute("INSERT INTO threat_logs (timestamp, message) VALUES (?, ?)", 
                 (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    conn.commit()
    conn.close()

def save_asset_log(obj, person, img_path):
    conn = sqlite3.connect('security.db')
    conn.execute("INSERT INTO asset_logs (timestamp, object_name, person_seen, image_path) VALUES (?, ?, ?, ?)", 
                 (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), obj, person, img_path))
    conn.commit()
    conn.close()

def generate_frames():
    global last_sms_time, last_log_time, loitering_start_time, last_welcome_time, last_asset_log_time
    process_this_frame = True
    current_person_name = "Unknown"
    is_admin = False

    while True:
        success, frame = camera.read()
        if not success: break
        
        # High Sensitivity Mode
        results = model(frame, verbose=False, conf=0.35)
        detected_classes = results[0].boxes.cls.tolist()
        annotated_frame = results[0].plot() 
        now = datetime.datetime.now()

        # 1. FACE RECOGNITION
        if process_this_frame:
            small = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, faces)
            
            current_person_name = "Unknown Person"
            is_admin = False

            for encoding in encodings:
                matches = face_recognition.compare_faces(known_face_encodings, encoding)
                if True in matches:
                    current_person_name = "Admin (KP Singh)"
                    is_admin = True
                    if last_welcome_time is None or (now - last_welcome_time).seconds > 60:
                        speak("Welcome Admin.")
                        last_welcome_time = now
            
            for (top, right, bottom, left) in faces:
                top*=4; right*=4; bottom*=4; left*=4
                color = (0,255,0) if is_admin else (0,0,255)
                cv2.rectangle(annotated_frame, (left,top), (right,bottom), color, 2)
                cv2.putText(annotated_frame, current_person_name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        process_this_frame = not process_this_frame

        # 2. ASSET TRACKING
        tracked_items = {64: "Mouse", 63: "Laptop", 67: "Phone"}
        for class_id in detected_classes:
            if class_id in tracked_items:
                item_name = tracked_items[class_id]
                # Log Asset every 5 seconds
                if item_name not in last_asset_log_time or (now - last_asset_log_time[item_name]).seconds > 5:
                    filename = f"evidence_{int(time.time())}.jpg"
                    filepath = os.path.join("static/evidence", filename)
                    cv2.imwrite(filepath, frame)
                    print(f"📦 Saved: {item_name}")
                    save_asset_log(item_name, current_person_name, filename)
                    last_asset_log_time[item_name] = now

        # 3. THREAT LOGIC (SPLIT TIMERS)
        if 67.0 in detected_classes: # Weapon/Phone
            
            # A. FAST LOOP (Logs + Voice) -> Every 2 Seconds
            if last_log_time is None or (now - last_log_time).seconds > 2:
                print("⚠️ WEAPON DETECTED (LOGGING)")
                speak("Weapon Detected.")
                save_log("CRITICAL: Weapon Detected")
                last_log_time = now

            # B. SLOW LOOP (SMS + Email) -> Every 60 Seconds
            if last_sms_time is None or (now - last_sms_time).seconds > 60:
                print("📨 SENDING ALERTS...")
                
                # Save Evidence Photo first
                evidence_path = "evidence.jpg"
                cv2.imwrite(evidence_path, frame)
                
                # Send Alerts
                send_sms_alert("ALERT: Weapon detected at ATM!")
                send_email_alert("🚨 SECURITY ALERT", "A weapon was detected. See attached photo.", evidence_path)
                
                last_sms_time = now

        if 0.0 in detected_classes and not is_admin: # Loitering
            if loitering_start_time is None: loitering_start_time = time.time()
            elapsed = int(time.time() - loitering_start_time)
            cv2.putText(annotated_frame, f"Loitering: {elapsed}s", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
            if elapsed > LOITERING_LIMIT:
                 if elapsed % 5 == 0: # Speak every 5 seconds
                    speak("Warning. Please leave.")
                    save_log(f"WARNING: Loitering ({elapsed}s)")
        else:
            loitering_start_time = None

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- WEB ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'password123':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/find_item', methods=['GET', 'POST'])
def find_item():
    if not session.get('logged_in'): return redirect(url_for('login'))
    result = None
    image = None
    if request.method == 'POST':
        item = request.form['item_name']
        conn = sqlite3.connect('security.db')
        c = conn.cursor()
        c.execute("SELECT timestamp, person_seen, image_path FROM asset_logs WHERE object_name LIKE ? ORDER BY id DESC LIMIT 1", ('%'+item+'%',))
        data = c.fetchone()
        conn.close()
        if data:
            result = f"🔍 FOUND: {item} seen on {data[0]} with {data[1]}"
            image = data[2] 
        else:
            result = "❌ Not Found"
    return render_template('search.html', result=result, image=image)

@app.route('/view_db')
def view_db():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect('security.db')
    c = conn.cursor()
    c.execute("SELECT * FROM threat_logs ORDER BY id DESC")
    threats = c.fetchall()
    c.execute("SELECT * FROM asset_logs ORDER BY id DESC")
    assets = c.fetchall()
    conn.close()
    return render_template('database.html', threats=threats, assets=assets)

@app.route('/get_alerts')
def get_alerts():
    conn = sqlite3.connect('security.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, message FROM threat_logs ORDER BY id DESC LIMIT 10")
    data = c.fetchall()
    conn.close()
    return jsonify([f"{r[0]} - {r[1]}" for r in data])

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True)