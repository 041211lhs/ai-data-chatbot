// Vercel 빌드 스크립트: 정적 파일을 dist/로 복사하고,
// 환경 변수 API_BASE_URL로 config.js를 만든다(코드에 서버 주소를 박아 두지 않기 위해).
const fs = require("fs");
const path = require("path");

const out = path.join(__dirname, "dist");
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out);
for (const f of ["index.html", "style.css", "app.js"]) {
  fs.copyFileSync(path.join(__dirname, f), path.join(out, f));
}

const apiBase = process.env.API_BASE_URL;
if (!apiBase) {
  console.error("API_BASE_URL 환경 변수가 없다. Vercel 프로젝트 설정에서 추가하라.");
  process.exit(1);
}
fs.writeFileSync(path.join(out, "config.js"), `window.API_BASE_URL = ${JSON.stringify(apiBase)};\n`);
console.log("빌드 완료, API_BASE_URL =", apiBase);
