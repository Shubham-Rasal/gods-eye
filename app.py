from flask import Flask, render_template, Response, jsonify
import cv2
import threading
import time
import os
from datetime import datetime

app = Flask(__name__)

# Global variables
camera = None
output = None
is_recording = False
recording_thread = None
segment_duration = 5  # seconds
current_segment_start = 0
frame_width = 640
frame_height = 480
fps = 30

def create_video_writer():
    """Create a new video writer for a segment"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"static/recordings/segment_{timestamp}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    return cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))

def generate_frames():
    """Generate frames for the video preview"""
    global camera
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        camera.set(cv2.CAP_PROP_FPS, fps)
    
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        
        # Add recording indicator if recording
        if is_recording:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)  # Red circle when recording
            
        # Convert frame to jpg
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def record_video():
    global camera, output, is_recording, current_segment_start
    
    # Create recordings directory if it doesn't exist
    os.makedirs('static/recordings', exist_ok=True)
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        camera.set(cv2.CAP_PROP_FPS, fps)
    
    output = create_video_writer()
    current_segment_start = time.time()
    
    while is_recording:
        ret, frame = camera.read()
        if ret:
            output.write(frame)
            
            # Check if it's time to start a new segment
            current_time = time.time()
            if current_time - current_segment_start >= segment_duration:
                output.release()
                output = create_video_writer()
                current_segment_start = current_time
    
    # Clean up
    if output is not None:
        output.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_recording')
def start_recording():
    global is_recording, recording_thread
    
    if not is_recording:
        is_recording = True
        recording_thread = threading.Thread(target=record_video)
        recording_thread.start()
        return jsonify({"status": "success", "message": "Recording started"})
    return jsonify({"status": "error", "message": "Already recording"})

@app.route('/stop_recording')
def stop_recording():
    global is_recording, recording_thread
    
    if is_recording:
        is_recording = False
        if recording_thread is not None:
            recording_thread.join()
        return jsonify({"status": "success", "message": "Recording stopped"})
    return jsonify({"status": "error", "message": "Not recording"})

@app.route('/release_camera')
def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)