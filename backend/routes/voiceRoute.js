// routes/voiceRoute.js
import express from "express";
import multer from "multer";
import { handleVoiceInput } from "../controllers/voiceController.js";

const router = express.Router();
const upload = multer({ dest: "uploads/" });

router.post("/voice-input", upload.single("file"), handleVoiceInput);

export default router;
