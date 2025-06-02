import express from "express";
import cors from "cors";
import axios from "axios";
import multer from "multer";
import FormData from "form-data";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

// Your MongoDB config and routes
import { connectDB } from "./config/db.js";
import forumRoute from "./routes/forumRoute.js";
import authRoute from "./routes/authRoute.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const upload = multer({ dest: "uploads/" });
const FASTAPI_BASE_URL = "https://gradientgang-279556857326.asia-south1.run.app";

// Middleware
app.use(express.json());
app.use(cors());

// ✅ Connect to MongoDB
connectDB();

// ✅ API routes - Your custom Node.js routes
app.use("/api/forum", forumRoute);
app.use("/api/user", authRoute);

// ✅ FastAPI Proxy Routes
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

// ✅ Static Frontend Support (for Docker/Production)
app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// Support frontend routing in SPA
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// ✅ Start the server
const PORT = process.env.PORT || 8080;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
