import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const website = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const targetDir = resolve(website, "public/download");
await mkdir(targetDir, { recursive: true });
await copyFile(resolve(website, "../scripts/install-local"), resolve(targetDir, "install-ninai-macos.sh"));
