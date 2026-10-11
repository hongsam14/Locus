// The page's own head (V9, FR-D10): what a browser tab, a bookmark and a link preview show
// before the app runs — the name, the purpose sentence, the language on screen and an icon.
import { existsSync, readFileSync } from "node:fs";
import { setLang } from "../i18n";
import { webPath } from "../test/paths";

const html = readFileSync(webPath("index.html"), "utf8");
const readme = readFileSync(webPath("../README.md"), "utf8");

describe("index.html (FR-D10)", () => {
  it("is in Korean, the default language on screen", () => {
    expect(html).toMatch(/<html lang="ko">/);
  });

  it("is named Locus and described by the purpose sentence", () => {
    expect(html).toMatch(/<title>Locus<\/title>/);
    const purpose = /^\*\*(.+)\*\*$/m.exec(readme)?.[1];
    expect(purpose).toBeTruthy();
    expect(html).toContain(`content="${purpose}"`);
  });

  it("has an icon the build serves", () => {
    expect(html).toMatch(/<link rel="icon" type="image\/svg\+xml" href="\/favicon.svg" \/>/);
    expect(existsSync(webPath("public/favicon.svg"))).toBe(true);
  });
});

describe("the document language follows the screen's (R-03: already so; kept)", () => {
  afterEach(() => setLang("ko"));

  it("changes with the display language", () => {
    setLang("en");
    expect(document.documentElement.lang).toBe("en");
    setLang("ko");
    expect(document.documentElement.lang).toBe("ko");
  });
});
