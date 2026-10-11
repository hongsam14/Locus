// The page's own head (V9, FR-D10): what a browser tab, a bookmark and a link preview show
// before the app runs — the name, the purpose sentence, the language on screen and an icon.
import { existsSync, readFileSync } from "node:fs";
import { setLang } from "../i18n";
import { webPath } from "../test/paths";

const html = readFileSync(webPath("index.html"), "utf8");
const icon = readFileSync(webPath("public/favicon.svg"), "utf8");
const css = readFileSync(webPath("src/index.css"), "utf8");
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

  it("has an icon the build serves, and it is an SVG a browser can read", () => {
    expect(html).toMatch(/<link rel="icon" type="image\/svg\+xml" href="\/favicon.svg" \/>/);
    expect(existsSync(webPath("public/favicon.svg"))).toBe(true);
    const svg = new DOMParser().parseFromString(icon, "image/svg+xml");
    expect(svg.getElementsByTagName("parsererror")).toHaveLength(0);
    expect(svg.documentElement.nodeName).toBe("svg");
  });

  // index.html and the icon sit outside src, where the design grep looks; their colours are
  // the theme's tokens, so a token change shows here (code review 01 #18, #20)
  it("colours the browser bar and the icon with the theme's tokens", () => {
    const token = (name: string) => new RegExp(`--color-${name}:\\s*(#[0-9a-f]{6})`, "i").exec(css)?.[1];
    const bg = token("bg");
    const accent = token("accent");
    expect(bg && accent).toBeTruthy();
    expect(html).toContain(`<meta name="theme-color" content="${bg}" />`);
    const fills = [...icon.matchAll(/fill="(#[0-9a-f]{6})"/gi)].map((m) => m[1]);
    expect(new Set(fills)).toEqual(new Set([bg, accent]));
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

  it("is the remembered language from the first load, before the server answers", async () => {
    // code review 01 #18: without the load-time line it stayed "ko" until /api/langs answered
    localStorage.setItem("locus.lang", "en");
    document.documentElement.lang = "ko";
    vi.resetModules();
    try {
      await import("../i18n");
      expect(document.documentElement.lang).toBe("en");
    } finally {
      localStorage.removeItem("locus.lang");
      vi.resetModules();
      document.documentElement.lang = "ko";
    }
  });
});
