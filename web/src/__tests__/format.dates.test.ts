// Dates follow the display language, not the browser (V2 BR-V2-14, TP-V2-5).
import { formatDate, formatDateTime, turnAt, turnLabel } from "../format";
import { setLang } from "../i18n";

const AT = "2026-10-02T12:00:00Z";

describe("dates and turns", () => {
  afterEach(() => setLang("ko"));

  it("formats a day in the display language, time zone fixed by the caller", () => {
    expect(formatDate(AT, "ko", "UTC")).toBe("2026년 10월 2일");
    expect(formatDate(AT, "en", "UTC")).toBe("Oct 2, 2026");
    expect(formatDateTime(AT, "en", "UTC")).toBe("Oct 2, 2026, 12:00 PM");
  });

  it("shows an unreadable date as it is", () => {
    expect(formatDate("not a date", "ko")).toBe("not a date");
  });

  it("names turns", () => {
    expect(turnLabel(4)).toBe("4턴째");
    expect(turnAt(4)).toBe("4턴");
    expect(turnAt(0)).toBe("시작");
    setLang("en");
    expect(turnLabel(4)).toBe("Turn 4");
    expect(turnAt(0)).toBe("Start");
    expect(turnLabel(4, "ko")).toBe("4턴째"); // a given language wins (FD, review § 2)
    expect(turnAt(4, "ko")).toBe("4턴");
  });
});
