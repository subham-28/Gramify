import express from "express";
import multer from "multer";
import { extractIngredientsFromImage } from "../controllers/imageController.js";

const router = express.Router();
const upload = multer({ dest: "uploads/" });

router.post("/upload", upload.single("file"), extractIngredientsFromImage);

export default router;
