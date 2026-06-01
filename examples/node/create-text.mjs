import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: process.env.AGENTPDF_BASE_URL });

const result = await client.createTextPdf({
  text: "Hello from a Node.js okpdf script.",
  outputPath: ".agentpdf-out/node-script.pdf",
});

const numbered = await client.addPageNumbers({
  inputPath: ".agentpdf-out/node-script.pdf",
  outputPath: ".agentpdf-out/node-script-numbered.pdf",
});

console.log(JSON.stringify({ created: result, numbered }, null, 2));
