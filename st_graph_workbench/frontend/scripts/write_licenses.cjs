const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const lock = JSON.parse(
    fs.readFileSync(path.join(root, "package-lock.json"), "utf8")
);
const sections = [
    "Third-party licenses for locked production frontend dependencies.\n",
];

for (const [directory, info] of Object.entries(lock.packages).sort()) {
    if (!directory || info.dev) continue;
    const packageDir = path.join(root, directory);
    const metadata = JSON.parse(
        fs.readFileSync(path.join(packageDir, "package.json"), "utf8")
    );
    if (metadata.version !== info.version) {
        throw new Error(
            `Run npm ci: ${directory} does not match package-lock.json`
        );
    }
    const files = fs
        .readdirSync(packageDir)
        .filter((name) =>
            /^(licen[cs]e|copying|notice)(\.(txt|md|rst))?$/i.test(name)
        )
        .sort();
    if (files.length === 0)
        throw new Error(`Missing license text: ${directory}`);
    sections.push(
        `\n=== ${metadata.name}@${info.version} (${metadata.license || "see below"}) ===\n`
    );
    for (const name of files) {
        sections.push(
            `\n${name}\n${fs.readFileSync(path.join(packageDir, name), "utf8").trim()}\n`
        );
    }
}

fs.writeFileSync(
    path.join(root, "build", "THIRD_PARTY_LICENSES.txt"),
    sections.join("")
);
