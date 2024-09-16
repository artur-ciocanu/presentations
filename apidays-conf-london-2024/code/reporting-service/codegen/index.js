const fs = require("fs");
const { JavaFileGenerator } = require("@asyncapi/modelina");
const SCHEMA_PATH = "../json-schemas/metrics-data.schema.json";
const OUTPUT_PATH = "src/main/java/org/demo/reporting/service";

async function generate() {
  const generator = new JavaFileGenerator();
  const schema = JSON.parse(fs.readFileSync(SCHEMA_PATH, "utf8"));
  
  await generator.generateToFiles(schema, OUTPUT_PATH, {
    packageName: "org.demo.reporting.service"
  });
}

generate();
