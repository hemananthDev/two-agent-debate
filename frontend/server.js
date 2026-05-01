const express = require("express");
const path = require("path");
const app = express();

app.use(express.static(path.join(__dirname)));
const server = app.listen(3000, () => console.log("Frontend running at http://localhost:3000"));
server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error("Port 3000 is already in use. Please free it and try again.");
  } else {
    console.error("Server error:", err.message);
  }
  process.exit(1);
});
