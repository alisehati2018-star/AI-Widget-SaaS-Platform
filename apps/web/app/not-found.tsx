// Global fallback for paths the locale middleware can't resolve. It must render
// its own <html>/<body> because it sits outside the [locale] root layout.
export default function GlobalNotFound() {
  return (
    <html lang="fa" dir="rtl">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0b14",
          color: "#eef0f6",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: "1.6rem", margin: "0 0 0.5rem" }}>۴۰۴ — صفحه پیدا نشد</h1>
          <p style={{ color: "#9aa0b4" }}>
            <a href="/" style={{ color: "#7c5cff" }}>
              بازگشت به خانه
            </a>
          </p>
        </div>
      </body>
    </html>
  );
}
