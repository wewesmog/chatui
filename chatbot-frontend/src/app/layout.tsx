import './globals.css'

export const metadata = {
  title: 'AI Chat Assistant',
  description: 'Your intelligent chat companion',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}