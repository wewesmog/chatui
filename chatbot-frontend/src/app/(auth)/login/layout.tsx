export default function LoginLayout({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
      <div className="min-h-screen bg-gray-50">
        {children}
      </div>
    )
  }