import { createServer } from "http";
import { parse } from "url";
import next from "next";
import { applyPersistedConfigToProcessEnv } from "./api/utils/persistedConfig";

const role = (process.env.SVD_APP_ROLE || "launchpad").toLowerCase();
if (role === "launchpad") {
  applyPersistedConfigToProcessEnv();
}

const port = parseInt(process.env.CDSW_APP_PORT || process.env.PORT || "3000", 10);
const dev = process.env.NODE_ENV !== "production";
const app = next({ dev });
const handle = app.getRequestHandler();
const label = role === "runtime" ? "SVD Runtime" : "SVD Launchpad";

app.prepare().then(() => {
  createServer((req, res) => {
    const parsedUrl = parse(req.url!, true);
    handle(req, res, parsedUrl);
  }).listen(port, "127.0.0.1", () => {
    console.log(`> ${label} on http://127.0.0.1:${port}`);
  });
});
