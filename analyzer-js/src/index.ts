import express from "express";
import type { Request, Response } from "express";
import { analyzePlaceholder } from "./analyzers/placeholder.js";

const app = express();
const port = process.env.PORT ? Number(process.env.PORT) : 4100;

app.use(express.json());

app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "pegazus-analyzer-js" });
});

app.post("/analyze", async (req: Request, res: Response) => {
  const { filePath } = req.body ?? {};
  if (typeof filePath !== "string" || filePath.length === 0) {
    res.status(400).json({ error: "Se requiere 'filePath' en el cuerpo de la peticion." });
    return;
  }

  const findings = await analyzePlaceholder(filePath);
  res.json({ findings });
});

app.listen(port, () => {
  console.log(`[pegazus-analyzer-js] escuchando en http://localhost:${port}`);
});
