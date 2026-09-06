import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "S Cosmetics | קוסמטיקה פרה-רפואית",
  description:
    "טיפולי פנים, אנטי אייג׳ינג ולייזר בהתאמה אישית ובסטנדרט מקצועי.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="he" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
