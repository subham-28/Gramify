// controllers/voiceController.js
import axios from "axios";
import fs from "fs";
import FormData from "form-data";

const FASTAPI_BASE_URL = "https://gradientgang-279556857326.asia-south1.run.app";

export const handleVoiceInput = async (req, res) => {
  const filePath = req.file.path;

  const formData = new FormData();
  formData.append("file", fs.createReadStream(filePath));

  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/voice-input/`, formData, {
      headers: formData.getHeaders(),
    });

    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /voice-input:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to process voice input." });
  } finally {
    try {
      fs.unlinkSync(filePath);
    } catch (err) {
      console.warn("⚠️ Could not delete temp voice file:", err.message);
    }
  }
};
