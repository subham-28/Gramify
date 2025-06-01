const express = require("express");
const cors = require("cors");
const axios = require("axios");
const multer = require("multer");
const FormData = require("form-data");
const fs = require("fs");
const path = require("path");

const app = express();
const upload = multer({ dest: "uploads/" });

app.use(express.json());
app.use(cors());

const FASTAPI_BASE_URL = "https://gradientgang-279556857326.asia-south1.run.app";

// ✅ Serve static frontend files from build output (assumes ./public exists after Docker build)
app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// Support SPA routing
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// 🔁 API Routes (proxy to FastAPI)

app.post("/convert", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/convert/`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /convert:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to convert recipe ingredient." });
  }
});

app.post("/refresh-data", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/refresh-data/`);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /refresh-data:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to refresh ingredient data." });
  }
});

app.get("/ingredients", async (req, res) => {
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/ingredients/`);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /ingredients:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to get ingredients." });
  }
});

app.get("/ingredients/:ingredientName", async (req, res) => {
  const name = req.params.ingredientName;
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/ingredients/${name}`);
    res.json(response.data);
  } catch (error) {
    console.error(`❌ Error fetching ingredient '${name}':`, error.message, error.response?.data);
    res.status(500).json({ error: `Failed to get ingredient: ${name}` });
  }
});

app.post("/ingredients", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/ingredients/`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /ingredients:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to add new ingredient." });
  }
});

app.post("/extract-ingredients", upload.single("file"), async (req, res) => {
  const filePath = req.file.path;
  const formData = new FormData();
  formData.append("file", fs.createReadStream(filePath));

  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/extract-ingredients/`, formData, {
      headers: formData.getHeaders(),
    });

    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /extract-ingredients:", error.message, error.response?.data);
    res.status(500).json({ error: "Failed to extract and convert from image." });
  } finally {
    // Safely remove temp file
    try {
      fs.unlinkSync(filePath);
    } catch (err) {
      console.warn("⚠️ Could not delete temp file:", err.message);
    }
  }
});

app.post("/voice-input", upload.single("file"), async (req, res) => {
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
      console.warn("⚠️ Could not delete temp file:", err.message);
    }
  }
});

// ✅ Start Server
const port = 8080;
app.listen(port, '0.0.0.0', () => {
  console.log(`Server running on port ${port}`);
});
