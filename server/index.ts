import express from "express";
import { createServer } from "http";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const server = createServer(app);

  // Serve static files from dist/public in production
  const staticPath =
    process.env.NODE_ENV === "production"
      ? path.resolve(__dirname, "public")
      : path.resolve(__dirname, "..", "dist", "public");

  app.use(express.static(staticPath));

  app.get("/api/proxy-site", async (req, res) => {
    try {
      const target = req.query.url as string;
      if (!target) {
        res.status(400).send("Missing url parameter");
        return;
      }
      let formatted = target.trim();
      if (!formatted.startsWith("http://") && !formatted.startsWith("https://")) {
        formatted = "https://" + formatted;
      }
      const response = await fetch(formatted, {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
        },
        redirect: "follow",
      });
      const contentType = response.headers.get("content-type") || "text/html";
      if (contentType.includes("text/html")) {
        let html = await response.text();
        const baseUrl = new URL(response.url || formatted);
        const baseTag = `<base href="${baseUrl.origin}${baseUrl.pathname.replace(/\/[^/]*$/, "/")}" />`;
        html = html.includes("<head>") ? html.replace("<head>", `<head>${baseTag}`) : baseTag + html;
        res.set("Content-Type", "text/html; charset=utf-8");
        res.send(html);
      } else {
        const buffer = Buffer.from(await response.arrayBuffer());
        res.set("Content-Type", contentType);
        res.send(buffer);
      }
    } catch (err: any) {
      res.status(500).send(`Unable to proxy site: ${err.message}`);
    }
  });

  // Handle client-side routing - serve index.html for all routes
  app.get("*", (_req, res) => {
    res.sendFile(path.join(staticPath, "index.html"));
  });

  const port = process.env.PORT || 3000;

  server.listen(port, () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}

startServer().catch(console.error);
