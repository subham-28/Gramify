import fs from "fs";
import axios from "axios";
import FormData from "form-data";

const FASTAPI_BASE_URL = "https://gradientgang-279556857326.asia-south1.run.app";

export const extractIngredientsFromImage = async (req, res) => {
  const filePath = req.file.path;
  const formData = new FormData();
  formData.append("file", fs.createReadStream(filePath));

  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/extract-ingredients/`, formData, {
      headers: formData.getHeaders(),
    });
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in image extraction:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to extract ingredients from image." });
  } finally {
    try {
      fs.unlinkSync(filePath);
    } catch (err) {
      console.warn("⚠️ Could not delete temp file:", err.message);
    }
  }
};
