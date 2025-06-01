const express = require("express");
const cors = require("cors");
const axios = require("axios");
const multer = require("multer");
const FormData = require("form-data");
const fs = require("fs");

const app = express();
const upload = multer({ dest: "uploads/" });

app.use(express.json());
app.use(cors());

const FASTAPI_BASE_URL = "https://gradientgang-279556857326.asia-south1.run.app";

// POST /convert
app.post("/convert", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/convert/`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /convert:", error.message);
    res.status(500).json({ error: "Failed to convert recipe ingredient." });
  }
});

// POST /refresh-data
app.post("/refresh-data", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/refresh-data/`);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /refresh-data:", error.message);
    res.status(500).json({ error: "Failed to refresh ingredient data." });
  }
});

// GET /ingredients
app.get("/ingredients", async (req, res) => {
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/ingredients/`);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /ingredients:", error.message);
    res.status(500).json({ error: "Failed to get ingredients." });
  }
});

// GET /ingredients/:ingredientName
app.get("/ingredients/:ingredientName", async (req, res) => {
  const name = req.params.ingredientName;
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/ingredients/${name}`);
    res.json(response.data);
  } catch (error) {
    console.error(`❌ Error fetching ingredient '${name}':`, error.message);
    res.status(500).json({ error: `Failed to get ingredient: ${name}` });
  }
});

// POST /ingredients
app.post("/ingredients", async (req, res) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/ingredients/`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /ingredients:", error.message);
    res.status(500).json({ error: "Failed to add new ingredient." });
  }
});

// POST /extract-ingredients
app.post("/extract-ingredients", upload.single("file"), async (req, res) => {
  try {
    const filePath = req.file.path;
    const formData = new FormData();
    formData.append("file", fs.createReadStream(filePath));

    const response = await axios.post(`${FASTAPI_BASE_URL}/extract-ingredients/`, formData, {
      headers: formData.getHeaders(),
    });

    fs.unlinkSync(filePath);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /extract-ingredients:", error.message);
    res.status(500).json({ error: "Failed to extract and convert from image." });
  }
});

// POST /voice-input
app.post("/voice-input", upload.single("file"), async (req, res) => {
  try {
    const filePath = req.file.path;
    const formData = new FormData();
    formData.append("file", fs.createReadStream(filePath));

    const response = await axios.post(`${FASTAPI_BASE_URL}/voice-input/`, formData, {
      headers: formData.getHeaders(),
    });

    fs.unlinkSync(filePath);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error in /voice-input:", error.message);
    res.status(500).json({ error: "Failed to process voice input." });
  }
});

// Server Start
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
