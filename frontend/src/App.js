import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [sessionId] = useState(() => Math.random().toString(36).substr(2, 9));
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
        setError("");
      }
    } catch (err) {
      setError("Camera access denied. Please allow camera permissions or upload an image instead.");
    }
  };

  // Capture image from camera
  const captureImage = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      
      context.drawImage(videoRef.current, 0, 0);
      const imageDataUrl = canvas.toDataURL('image/jpeg', 0.8);
      setCapturedImage(imageDataUrl);
      stopCamera();
    }
  };

  // Stop camera
  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  // Handle file upload
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setCapturedImage(e.target.result);
        setError("");
        setSuccess("Image uploaded successfully!");
      };
      reader.readAsDataURL(file);
    }
  };

  // Retake photo
  const retakePhoto = () => {
    setCapturedImage(null);
    setResults(null);
    setError("");
    setSuccess("");
  };

  // Analyze pill
  const analyzePill = async () => {
    if (!capturedImage) {
      setError("Please capture or upload an image first.");
      return;
    }

    setAnalyzing(true);
    setError("");
    setResults(null);

    try {
      // Convert image to base64 if it's not already
      const base64Image = capturedImage.includes('base64,') 
        ? capturedImage.split('base64,')[1] 
        : capturedImage;

      const response = await axios.post(`${API}/analyze-pill`, {
        image_base64: base64Image,
        session_id: sessionId
      });

      setResults(response.data);
      setSuccess("Pill analyzed successfully!");
    } catch (err) {
      setError("Failed to analyze pill. Please try again.");
      console.error("Analysis error:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  // Emergency actions
  const reportAdverseEvent = () => {
    alert("Emergency feature: Contact your healthcare provider immediately if experiencing adverse effects. Call emergency services if severe.");
  };

  const findDoctor = () => {
    alert("Emergency feature: Use your local directory or call emergency services for immediate medical attention.");
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="app-container">
      <div className="container">
        <div className="header">
          <div className="logo">💊</div>
          <div className="app-name">PillWise</div>
          <div className="tagline">AI-powered pill identification with Ayurvedic alternatives</div>
        </div>

        <div className="main-content">
          <div className="upload-section">
            <div className="camera-container">
              {!cameraActive && !capturedImage && (
                <div className="camera-placeholder">
                  <div className="camera-icon">📷</div>
                  <div>Take a photo of your pill</div>
                  <small>Ensure good lighting and clear visibility</small>
                </div>
              )}
              
              {cameraActive && (
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  className="camera-feed"
                />
              )}
              
              {capturedImage && (
                <img 
                  src={capturedImage} 
                  alt="Captured pill" 
                  className="captured-image"
                />
              )}
            </div>

            {!cameraActive && !capturedImage && (
              <div className="camera-controls">
                <button className="btn btn-primary" onClick={startCamera}>
                  📷 Open Camera
                </button>
                <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>
                  📁 Upload Image
                </button>
                <input 
                  type="file" 
                  ref={fileInputRef}
                  accept="image/*" 
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </div>
            )}

            {cameraActive && (
              <div className="camera-controls">
                <button className="btn btn-primary" onClick={captureImage}>
                  📸 Capture
                </button>
                <button className="btn btn-secondary" onClick={stopCamera}>
                  ❌ Cancel
                </button>
              </div>
            )}

            {capturedImage && !analyzing && (
              <div className="camera-controls">
                <button className="btn btn-primary" onClick={analyzePill}>
                  🔍 Analyze Pill
                </button>
                <button className="btn btn-secondary" onClick={retakePhoto}>
                  🔄 Retake
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {success && (
            <div className="success-message">
              {success}
            </div>
          )}

          {analyzing && (
            <div className="loading">
              <div className="spinner"></div>
              <div>Analyzing your pill using AI...</div>
              <small>Checking against comprehensive pill database</small>
            </div>
          )}

          {results && (
            <div className="results-section">
              <div className="result-card">
                <div className="result-title">🔍 Pill Identification</div>
                <div className="result-content">
                  <strong>{results.pill_name}</strong>
                  <p>{results.pill_description}</p>
                </div>
                <div className="confidence-meter">
                  <span>Confidence:</span>
                  <div className="confidence-bar">
                    <div 
                      className="confidence-fill" 
                      style={{ width: `${results.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span>{Math.round(results.confidence * 100)}%</span>
                </div>
              </div>

              <div className="result-card">
                <div className="result-title">💊 Uses & Dosage</div>
                <div className="result-content">
                  <div className="info-section">
                    <strong>Medical Uses:</strong>
                    <p>{results.uses}</p>
                  </div>
                  <div className="info-section">
                    <strong>Dosage:</strong>
                    <p>{results.dosage}</p>
                  </div>
                </div>
              </div>

              <div className="result-card">
                <div className="result-title">⚠️ Safety Information</div>
                <div className="result-content">
                  <div className="info-section">
                    <strong>Side Effects:</strong>
                    <p>{results.side_effects}</p>
                  </div>
                  <div className="info-section">
                    <strong>Safety Precautions:</strong>
                    <p>{results.safety_info}</p>
                  </div>
                </div>
              </div>

              <div className="result-card">
                <div className="result-title">🌿 Ayurvedic Alternatives</div>
                <div className="result-content">
                  <div className="ayurveda-alternatives">
                    {results.ayurvedic_alternatives}
                  </div>
                </div>
              </div>

              <div className="result-card">
                <div className="result-title">🏥 Emergency Actions</div>
                <div className="result-content">
                  <div className="emergency-actions">
                    <button className="btn btn-danger" onClick={reportAdverseEvent}>
                      ⚠️ Report Side Effect
                    </button>
                    <button className="btn btn-success" onClick={findDoctor}>
                      👨‍⚕️ Find Doctor
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="disclaimer">
            <strong>⚠️ Important Disclaimer:</strong> This app is for informational purposes only and should not replace professional medical advice. Always consult with a healthcare professional before making any changes to your medication. Never stop taking prescribed medication without medical supervision. In case of emergency, call your local emergency number immediately.
          </div>
        </div>
      </div>

      {/* Hidden canvas for image capture */}
      <canvas ref={canvasRef} style={{ display: 'none' }}></canvas>
    </div>
  );
}

export default App;